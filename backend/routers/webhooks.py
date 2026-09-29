import secrets
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models
import schemas
from services.notification_service import validate_webhook_url, notification_service

router = APIRouter(prefix="/webhooks", tags=["Webhook Notification Infrastructure"])


def _check_webhook_tenant_access(endpoint: models.WebhookEndpoint, current_user: models.User):
    if current_user.role != "SUPER_ADMIN" and str(endpoint.org_id) != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access webhook endpoints belonging to another organization"
        )


@router.get("", response_model=List[schemas.WebhookEndpointSchema])
def list_webhooks(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.WebhookEndpoint)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.WebhookEndpoint.org_id == current_user.org_id)
    return query.order_by(models.WebhookEndpoint.created_at.desc()).all()


@router.post("", response_model=schemas.WebhookCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    req: schemas.WebhookCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.org_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization to create webhooks.")

    # 1. SSRF URL Validation
    is_valid, err = validate_webhook_url(req.url)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    # 2. Generate Cryptographic Secret
    raw_secret = f"whsec_{secrets.token_hex(24)}"
    secret_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
    secret_preview = f"whsec_****{raw_secret[-6:]}"

    endpoint = models.WebhookEndpoint(
        org_id=current_user.org_id,
        name=req.name,
        url=req.url.strip(),
        secret_hash=secret_hash,
        secret_preview=secret_preview,
        secret_key=raw_secret,
        is_active=True,
        event_types=req.event_types or ["*"]
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)

    # 3. Audit Log
    audit = models.AuditLog(
        event_type="WEBHOOK_CREATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CREATE_WEBHOOK_ENDPOINT",
        resource=f"webhook:{endpoint.id}",
        result="SUCCESS",
        metadata_json={"name": endpoint.name, "url": endpoint.url, "org_id": str(endpoint.org_id)}
    )
    db.add(audit)
    db.commit()

    return schemas.WebhookCreatedResponse(
        id=str(endpoint.id),
        org_id=str(endpoint.org_id),
        name=endpoint.name,
        url=endpoint.url,
        secret_preview=endpoint.secret_preview,
        secret=raw_secret,  # Only returned once!
        is_active=endpoint.is_active,
        event_types=endpoint.event_types or [],
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at
    )


# ==================== DEAD-LETTER & RETRY ====================

@router.get("/dead-letter")
def list_dead_letter_deliveries(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists webhook deliveries that exhausted all retries (DEAD_LETTER or FAILED)."""
    # Get this org's webhook endpoints
    endpoint_q = db.query(models.WebhookEndpoint)
    if current_user.role != "SUPER_ADMIN":
        endpoint_q = endpoint_q.filter(models.WebhookEndpoint.org_id == current_user.org_id)

    endpoint_ids = [str(e.id) for e in endpoint_q.all()]
    if not endpoint_ids:
        return []

    deliveries = db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.webhook_id.in_(endpoint_ids),
        models.WebhookDelivery.status.in_(["DEAD_LETTER", "FAILED"])
    ).order_by(models.WebhookDelivery.created_at.desc()).limit(100).all()

    result = []
    for d in deliveries:
        ep = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == d.webhook_id).first()
        result.append({
            "delivery_id": str(d.id),
            "webhook_id": str(d.webhook_id),
            "endpoint_name": ep.name if ep else "Unknown",
            "endpoint_url": ep.url if ep else "Unknown",
            "event_type": d.event_type,
            "status": d.status,
            "attempt_count": d.attempt_count,
            "last_error": d.error_message,
            "response_code": d.response_code,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })
    return result


@router.post("/dead-letter/{delivery_id}/retry")
def retry_dead_letter_delivery(
    delivery_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retries a dead-letter delivery by creating a NEW delivery attempt (never corrupting history)."""
    original = db.query(models.WebhookDelivery).filter(models.WebhookDelivery.id == delivery_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Delivery not found")

    # Verify tenant access
    endpoint = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == original.webhook_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    _check_webhook_tenant_access(endpoint, current_user)

    if original.status not in ("DEAD_LETTER", "FAILED"):
        raise HTTPException(status_code=400, detail="Only DEAD_LETTER or FAILED deliveries can be retried")

    # Create a new delivery attempt using the original payload
    new_delivery = notification_service.dispatch_webhook_delivery(
        db=db,
        endpoint=endpoint,
        event_type=original.event_type,
        payload_data=original.payload_json or {},
        max_retries=1  # Single retry attempt for manual retries
    )

    if not new_delivery:
        raise HTTPException(status_code=400, detail="Webhook endpoint is disabled")

    # Audit the retry
    audit = models.AuditLog(
        event_type="WEBHOOK_DEAD_LETTER_RETRY",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="RETRY_DEAD_LETTER_DELIVERY",
        resource=f"delivery:{delivery_id}",
        result=new_delivery.status,
        metadata_json={
            "original_delivery_id": delivery_id,
            "new_delivery_id": str(new_delivery.id),
            "endpoint_id": str(endpoint.id)
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "original_delivery_id": delivery_id,
        "new_delivery_id": str(new_delivery.id),
        "new_delivery_status": new_delivery.status
    }


@router.get("/{webhook_id}", response_model=schemas.WebhookEndpointSchema)
def get_webhook(
    webhook_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    endpoint = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == webhook_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    _check_webhook_tenant_access(endpoint, current_user)
    return endpoint


@router.patch("/{webhook_id}", response_model=schemas.WebhookEndpointSchema)
def update_webhook(
    webhook_id: str,
    req: schemas.WebhookUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    endpoint = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == webhook_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    _check_webhook_tenant_access(endpoint, current_user)

    if req.name is not None:
        endpoint.name = req.name
    if req.url is not None:
        is_valid, err = validate_webhook_url(req.url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=err)
        endpoint.url = req.url.strip()
    if req.is_active is not None:
        endpoint.is_active = req.is_active
    if req.event_types is not None:
        endpoint.event_types = req.event_types

    db.commit()
    db.refresh(endpoint)

    audit = models.AuditLog(
        event_type="WEBHOOK_UPDATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="UPDATE_WEBHOOK_ENDPOINT",
        resource=f"webhook:{endpoint.id}",
        result="SUCCESS",
        metadata_json={"is_active": endpoint.is_active, "name": endpoint.name}
    )
    db.add(audit)
    db.commit()

    return endpoint


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    endpoint = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == webhook_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    _check_webhook_tenant_access(endpoint, current_user)

    db.delete(endpoint)
    db.commit()

    audit = models.AuditLog(
        event_type="WEBHOOK_DELETED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="DELETE_WEBHOOK_ENDPOINT",
        resource=f"webhook:{webhook_id}",
        result="SUCCESS"
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": "Webhook endpoint deleted successfully"}


@router.get("/{webhook_id}/deliveries", response_model=List[schemas.WebhookDeliverySchema])
def list_webhook_deliveries(
    webhook_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    endpoint = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == webhook_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    _check_webhook_tenant_access(endpoint, current_user)

    deliveries = db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.webhook_id == webhook_id
    ).order_by(models.WebhookDelivery.created_at.desc()).limit(100).all()

    return deliveries


@router.post("/{webhook_id}/test", response_model=schemas.WebhookDeliverySchema)
def test_webhook_delivery(
    webhook_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    endpoint = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == webhook_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    _check_webhook_tenant_access(endpoint, current_user)

    delivery = notification_service.dispatch_webhook_delivery(
        db=db,
        endpoint=endpoint,
        event_type="test.ping",
        payload_data={
            "resource_type": "webhook_test",
            "resource_id": str(endpoint.id),
            "data": {
                "message": "AgentGuard test webhook event",
                "triggered_by": current_user.email
            }
        }
    )
    return delivery


