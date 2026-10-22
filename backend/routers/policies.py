import datetime
from typing import List, Optional, cast
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user, require_permission
from core.permissions import (
    PERM_POLICY_VIEW,
    PERM_POLICY_CREATE,
    PERM_POLICY_UPDATE,
    PERM_POLICY_DELETE,
    PERM_POLICY_ENABLE,
    PERM_POLICY_DISABLE,
)
import models
import schemas
from engines.policy_engine import policy_engine
from engines.policy_evaluator import validate_rule_syntax

router = APIRouter(prefix="/policies", tags=["Governance Policies"])


def _check_policy_tenant_access(policy: models.Policy, current_user: models.User):
    if str(current_user.role) != "SUPER_ADMIN" and str(policy.org_id) != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access policies belonging to another organization"
        )


def _to_policy_schema(p: models.Policy, rules: list) -> schemas.PolicySchema:
    return schemas.PolicySchema(
        id=str(p.id),
        org_id=str(p.org_id),
        name=str(p.name),
        category=str(p.category),
        priority=int(getattr(p, "priority", 0) or 0),
        status=str(p.status),
        version=str(p.version),
        created_at=cast(datetime.datetime, p.created_at),
        rules=[schemas.PolicyRuleSchema.model_validate(r) for r in rules],
        rules_count=len(rules)
    )


@router.get("", response_model=List[schemas.PolicySchema])
def list_policies(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: models.User = Depends(require_permission(PERM_POLICY_VIEW)),
    db: Session = Depends(get_db)
):
    query = db.query(models.Policy)
    if str(current_user.role) != "SUPER_ADMIN":
        query = query.filter(models.Policy.org_id == current_user.org_id)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(models.Policy.status == status_filter.upper())
    
    policies = query.order_by(models.Policy.priority.asc(), models.Policy.created_at.asc()).all()
    
    # Populate rules and counts
    result = []
    for p in policies:
        p_rules = db.query(models.PolicyRule).filter(models.PolicyRule.policy_id == p.id).all()
        result.append(_to_policy_schema(p, p_rules))
    return result


@router.get("/{policy_id}", response_model=schemas.PolicySchema)
def get_policy(
    policy_id: str,
    current_user: models.User = Depends(require_permission(PERM_POLICY_VIEW)),
    db: Session = Depends(get_db)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    _check_policy_tenant_access(policy, current_user)

    rules = db.query(models.PolicyRule).filter(models.PolicyRule.policy_id == policy.id).all()
    return _to_policy_schema(policy, rules)


@router.post("", response_model=schemas.PolicySchema, status_code=status.HTTP_201_CREATED)
def create_policy(
    req: schemas.PolicyCreateRequest,
    target_org_id: Optional[str] = Query(None),
    current_user: models.User = Depends(require_permission(PERM_POLICY_CREATE)),
    db: Session = Depends(get_db)
):
    org_id = current_user.org_id
    if str(current_user.role) == "SUPER_ADMIN" and target_org_id:
        org_id = target_org_id
    if org_id is None:
        raise HTTPException(status_code=400, detail="Organization ID is required to create a policy.")

    # Validate all initial rules if provided
    if req.rules:
        for r in req.rules:
            is_valid, err = validate_rule_syntax(r.condition_expression)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid rule condition '{r.condition_expression}': {err}")
            if r.decision_output.upper() not in ["ALLOW", "REVIEW", "REFUSE"]:
                raise HTTPException(status_code=400, detail=f"Invalid decision_output '{r.decision_output}'. Must be ALLOW, REVIEW, or REFUSE.")

    new_policy = models.Policy(
        org_id=org_id,
        name=req.name,
        category=req.category.upper(),
        priority=req.priority,
        status=req.status.upper(),
        version=req.version
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)

    created_rules = []
    if req.rules:
        for r in req.rules:
            rule = models.PolicyRule(
                policy_id=new_policy.id,
                condition_expression=r.condition_expression,
                decision_output=r.decision_output.upper(),
                risk_delta=r.risk_delta,
                description=r.description
            )
            db.add(rule)
            created_rules.append(rule)
        db.commit()
        for r in created_rules:
            db.refresh(r)

    # Log audit
    audit = models.AuditLog(
        event_type="POLICY_CREATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CREATE_POLICY",
        resource=f"policy:{new_policy.id}",
        result="SUCCESS",
        metadata_json={"policy_name": new_policy.name, "org_id": str(org_id), "rules_count": len(created_rules)}
    )
    db.add(audit)
    db.commit()

    return _to_policy_schema(new_policy, created_rules)


@router.patch("/{policy_id}", response_model=schemas.PolicySchema)
def update_policy(
    policy_id: str,
    req: schemas.PolicyUpdateRequest,
    current_user: models.User = Depends(require_permission(PERM_POLICY_UPDATE)),
    db: Session = Depends(get_db)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    _check_policy_tenant_access(policy, current_user)

    if req.name is not None:
        setattr(policy, "name", req.name)
    if req.category is not None:
        setattr(policy, "category", req.category.upper())
    if req.priority is not None:
        setattr(policy, "priority", req.priority)
    if req.status is not None:
        setattr(policy, "status", req.status.upper())
    if req.version is not None:
        setattr(policy, "version", req.version)

    db.commit()
    db.refresh(policy)

    # Log audit
    audit = models.AuditLog(
        event_type="POLICY_UPDATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="UPDATE_POLICY",
        resource=f"policy:{policy.id}",
        result="SUCCESS",
        metadata_json={"policy_id": str(policy.id), "status": policy.status, "priority": policy.priority}
    )
    db.add(audit)
    db.commit()

    rules = db.query(models.PolicyRule).filter(models.PolicyRule.policy_id == policy.id).all()
    return _to_policy_schema(policy, rules)


@router.post("/{policy_id}/toggle", response_model=schemas.PolicySchema)
def toggle_policy_status(
    policy_id: str,
    current_user: models.User = Depends(require_permission(PERM_POLICY_UPDATE)),
    db: Session = Depends(get_db)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    _check_policy_tenant_access(policy, current_user)

    setattr(policy, "status", "DISABLED" if str(policy.status) == "ACTIVE" else "ACTIVE")
    db.commit()
    db.refresh(policy)

    rules = db.query(models.PolicyRule).filter(models.PolicyRule.policy_id == policy.id).all()
    return _to_policy_schema(policy, rules)


@router.delete("/{policy_id}")
def delete_policy(
    policy_id: str,
    current_user: models.User = Depends(require_permission(PERM_POLICY_DELETE)),
    db: Session = Depends(get_db)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    _check_policy_tenant_access(policy, current_user)

    # Delete rules
    db.query(models.PolicyRule).filter(models.PolicyRule.policy_id == policy.id).delete()
    db.delete(policy)
    db.commit()

    return {"status": "SUCCESS", "message": f"Policy {policy_id} deleted successfully"}


# --- Policy Rules Sub-endpoints ---

@router.post("/{policy_id}/rules", response_model=schemas.PolicyRuleSchema, status_code=status.HTTP_201_CREATED)
def add_policy_rule(
    policy_id: str,
    req: schemas.PolicyRuleCreateRequest,
    current_user: models.User = Depends(require_permission(PERM_POLICY_UPDATE)),
    db: Session = Depends(get_db)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    _check_policy_tenant_access(policy, current_user)

    is_valid, err = validate_rule_syntax(req.condition_expression)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid rule condition: {err}")

    decision_out = req.decision_output.upper()
    if decision_out not in ["ALLOW", "REVIEW", "REFUSE"]:
        raise HTTPException(status_code=400, detail=f"Invalid decision_output '{req.decision_output}'. Must be ALLOW, REVIEW, or REFUSE.")

    rule = models.PolicyRule(
        policy_id=policy.id,
        condition_expression=req.condition_expression,
        decision_output=decision_out,
        risk_delta=req.risk_delta,
        description=req.description
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return schemas.PolicyRuleSchema.model_validate(rule)


@router.patch("/{policy_id}/rules/{rule_id}", response_model=schemas.PolicyRuleSchema)
def update_policy_rule(
    policy_id: str,
    rule_id: str,
    req: schemas.PolicyRuleUpdateRequest,
    current_user: models.User = Depends(require_permission(PERM_POLICY_UPDATE)),
    db: Session = Depends(get_db)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    _check_policy_tenant_access(policy, current_user)

    rule = db.query(models.PolicyRule).filter(
        models.PolicyRule.id == rule_id,
        models.PolicyRule.policy_id == policy.id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Policy rule not found")

    if req.condition_expression is not None:
        is_valid, err = validate_rule_syntax(req.condition_expression)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid rule condition: {err}")
        setattr(rule, "condition_expression", req.condition_expression)

    if req.decision_output is not None:
        decision_out = req.decision_output.upper()
        if decision_out not in ["ALLOW", "REVIEW", "REFUSE"]:
            raise HTTPException(status_code=400, detail=f"Invalid decision_output '{req.decision_output}'. Must be ALLOW, REVIEW, or REFUSE.")
        setattr(rule, "decision_output", decision_out)

    if req.risk_delta is not None:
        setattr(rule, "risk_delta", req.risk_delta)
    if req.description is not None:
        setattr(rule, "description", req.description)

    db.commit()
    db.refresh(rule)
    return schemas.PolicyRuleSchema.model_validate(rule)


@router.delete("/{policy_id}/rules/{rule_id}")
def delete_policy_rule(
    policy_id: str,
    rule_id: str,
    current_user: models.User = Depends(require_permission(PERM_POLICY_DELETE)),
    db: Session = Depends(get_db)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    _check_policy_tenant_access(policy, current_user)

    rule = db.query(models.PolicyRule).filter(
        models.PolicyRule.id == rule_id,
        models.PolicyRule.policy_id == policy.id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Policy rule not found")

    db.delete(rule)
    db.commit()
    return {"status": "SUCCESS", "message": f"Rule {rule_id} deleted successfully"}


@router.post("/evaluate")
def evaluate_policy(
    agent_name: str,
    action: str,
    resource: str,
    amount: float = 0.0,
    risk_score: int = 15,
    agent_status: str = "NORMAL",
    target_org_id: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.org_id
    if str(current_user.role) == "SUPER_ADMIN" and target_org_id:
        org_id = target_org_id

    return policy_engine.evaluate_action(
        db=db,
        org_id=str(org_id) if org_id is not None else None,
        agent_name=agent_name,
        action=action,
        resource=resource,
        amount=amount,
        risk_score=risk_score,
        agent_status=agent_status,
        user_role=str(current_user.role)
    )
