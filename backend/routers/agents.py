import random, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from ws_manager import manager as ws_manager
from core.deps import get_current_user, check_license_limit, require_permission
from core.permissions import (
    has_permission,
    PERM_AGENT_VIEW,
    PERM_AGENT_CREATE,
    PERM_AGENT_UPDATE,
    PERM_AGENT_SUSPEND,
    PERM_AGENT_RESUME,
    PERM_AGENT_BUDGET_UPDATE,
    PERM_USER_ROLE_ASSIGN,
)

router = APIRouter(prefix="/agents", tags=["Agent Management"])

@router.get("", response_model=list[schemas.AgentSchema])
def list_agents(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "SUPER_ADMIN":
        return db.query(models.Agent).all()
    return db.query(models.Agent).filter(models.Agent.org_id == current_user.org_id).all()

@router.post("", response_model=schemas.AgentSchema)
async def create_agent(
    req: schemas.AgentCreateRequest,
    current_user: models.User = Depends(require_permission(PERM_AGENT_CREATE)),
    db: Session = Depends(get_db)
):
    # 1. Reject attempts to create agents under another organization
    if req.org_id and current_user.role != "SUPER_ADMIN" and str(req.org_id) != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot create an AI agent under another organization"
        )

    # 2. Enforce License Limit for Agents
    check_license_limit(str(current_user.org_id), "agents", db)

    org_id = current_user.org_id
    owner_id = current_user.id

    # Handle requested owner_id with strict tenant validation and status checking
    if req.owner_id:
        target_owner = db.query(models.User).filter(models.User.id == req.owner_id).first()
        if not target_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requested owner with ID {req.owner_id} not found"
            )
        if current_user.role != "SUPER_ADMIN" and str(target_owner.org_id) != str(org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Agent owner must belong to the same organization"
            )
        if target_owner.status in ("SUSPENDED", "DEACTIVATED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot assign agent to owner with status '{target_owner.status}'"
            )
        owner_id = target_owner.id

    code_num = db.query(models.Agent).count() + 101
    agent_code = f"AG-{code_num}"

    agent = models.Agent(
        agent_code=agent_code,
        org_id=org_id,
        owner_id=owner_id,
        name=req.name,
        department=req.department or "Operations",
        purpose=req.purpose or "Autonomous AI Agent Workflow",
        model_name=req.model_name,
        model_version=req.model_version,
        environment=req.environment,
        autonomy_level=req.autonomy_level,
        status="NORMAL",
        risk_score=15,
        trust_score=95,
        daily_budget=req.daily_budget
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    # Create Passport with cryptographic Ed25519 asymmetric signature
    passport = models.AgentPassport(
        agent_id=agent.id,
        passport_number=f"AG-PASSPORT-{random.randint(100000, 999999)}",
        digital_signature="pending",
        issued_at=datetime.datetime.utcnow(),
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
        verification_status="VERIFIED",
        algorithm="Ed25519",
        key_id="agentguard-root-ed25519-v1",
        passport_version="1.0"
    )
    from services.passport_service import passport_service
    passport_service.sign_passport(agent, passport)
    db.add(passport)

    # Create Behavior Profile, Reputation, Circuit Breaker & Budget
    profile = models.BehaviorProfile(agent_id=agent.id, avg_daily_actions=200, baseline_spending=req.daily_budget * 0.25)
    reputation = models.ReputationScore(agent_id=agent.id, trust_score=95, successful_tasks=0)
    cb = models.CircuitBreaker(agent_id=agent.id, state="NORMAL")
    budget = models.Budget(agent_id=agent.id, daily_limit=req.daily_budget, monthly_limit=req.daily_budget * 30)

    db.add_all([profile, reputation, cb, budget])
    db.commit()
    db.refresh(agent)

    await ws_manager.broadcast({
        "type": "AGENT_CREATED",
        "agent_code": agent.agent_code,
        "name": agent.name,
        "department": agent.department,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return agent

@router.get("/{id}", response_model=schemas.AgentSchema)
def get_agent(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view AI agent belonging to another organization"
        )

    return agent

@router.get("/{id}/passport")
def get_agent_passport(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view Agent Passport belonging to another organization"
        )

    passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent.id).first()
    owner = db.query(models.User).filter(models.User.id == agent.owner_id).first()
    permissions = db.query(models.Permission).filter(models.Permission.agent_id == agent.id).all()
    credentials = db.query(models.AgentCredential).filter(models.AgentCredential.agent_id == agent.id).all()

    return {
        "agent": agent,
        "passport": passport,
        "owner_name": owner.full_name if owner else "System Owner",
        "organization_name": agent.organization.name if agent.organization else "AgentGuard Org",
        "permissions_count": len(permissions),
        "credentials": [c.credential_type for c in credentials]
    }

@router.patch("/{id}", response_model=schemas.AgentSchema)
async def update_agent(
    id: str,
    req: schemas.AgentUpdateRequest,
    current_user: models.User = Depends(require_permission(PERM_AGENT_UPDATE)),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify an AI agent belonging to another organization"
        )

    # Validate owner_id update if requested
    if req.owner_id is not None:
        target_owner = db.query(models.User).filter(models.User.id == req.owner_id).first()
        if not target_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target owner user with ID {req.owner_id} not found"
            )
        if current_user.role != "SUPER_ADMIN" and str(target_owner.org_id) != str(agent.org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Agent owner must belong to the same organization"
            )
        if target_owner.status in ("SUSPENDED", "DEACTIVATED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot assign agent to owner with status '{target_owner.status}'"
            )

        if req.owner_id != agent.owner_id:
            if not has_permission(current_user.role, PERM_USER_ROLE_ASSIGN) and current_user.role != "SUPER_ADMIN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Insufficient privileges to reassign agent ownership"
                )
            old_owner_id = agent.owner_id
            agent.owner_id = target_owner.id
            audit_owner = models.AuditLog(
                org_id=agent.org_id,
                event_type="AGENT_OWNER_CHANGE",
                actor_type="USER",
                actor_id=str(current_user.id),
                action="CHANGE_OWNER",
                resource=f"agent:{agent.agent_code}",
                result="SUCCESS",
                metadata_json={
                    "agent_id": str(agent.id),
                    "agent_code": agent.agent_code,
                    "old_owner_id": str(old_owner_id),
                    "new_owner_id": str(target_owner.id),
                    "actor_email": current_user.email
                }
            )
            db.add(audit_owner)

    if req.name is not None:
        agent.name = req.name
    if req.department is not None:
        agent.department = req.department
    if req.purpose is not None:
        agent.purpose = req.purpose
    if req.model_name is not None:
        agent.model_name = req.model_name
    if req.model_version is not None:
        agent.model_version = req.model_version
    if req.environment is not None:
        agent.environment = req.environment
    if req.autonomy_level is not None:
        if req.autonomy_level != agent.autonomy_level:
            if current_user.role not in ("ADMIN", "SECURITY_OFFICER", "SUPER_ADMIN"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Only administrators or security officers can modify agent autonomy levels"
                )
        agent.autonomy_level = req.autonomy_level

    if req.daily_budget is not None:
        if not has_permission(current_user.role, PERM_AGENT_BUDGET_UPDATE) and current_user.role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Insufficient privileges to update agent budget"
            )
        agent.daily_budget = req.daily_budget
        budget = db.query(models.Budget).filter(models.Budget.agent_id == agent.id).first()
        if budget:
            budget.daily_limit = req.daily_budget
            budget.monthly_limit = req.daily_budget * 30
        profile = db.query(models.BehaviorProfile).filter(models.BehaviorProfile.agent_id == agent.id).first()
        if profile:
            profile.baseline_spending = req.daily_budget * 0.25
        audit_budget = models.AuditLog(
            org_id=agent.org_id,
            event_type="AGENT_BUDGET_UPDATE",
            actor_type="USER",
            actor_id=str(current_user.id),
            action="UPDATE_BUDGET",
            resource=f"agent:{agent.agent_code}",
            result="SUCCESS",
            metadata_json={
                "agent_id": str(agent.id),
                "agent_code": agent.agent_code,
                "daily_budget": req.daily_budget,
                "actor_email": current_user.email
            }
        )
        db.add(audit_budget)

    db.commit()
    db.refresh(agent)
    return agent

@router.post("/{id}/suspend")
async def suspend_agent(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if not has_permission(current_user.role, PERM_AGENT_SUSPEND):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to suspend an agent"
        )

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot suspend AI agent belonging to another organization"
        )

    agent.status = "SUSPENDED"
    cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()
    if cb:
        cb.state = "SUSPENDED"
        cb.trigger_reason = "MANUAL_SUSPENSION_KILL_SWITCH"
        cb.tripped_at = datetime.datetime.utcnow()

    db.query(models.CapabilityToken).filter(models.CapabilityToken.agent_id == agent.id).update({"status": "REVOKED"})

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="AGENT_SUSPENDED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="SUSPEND_AGENT",
        resource=f"agent:{agent.agent_code}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "actor_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    await ws_manager.broadcast({
        "type": "AGENT_SUSPENDED",
        "agent_code": agent.agent_code,
        "name": agent.name,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {"status": "SUCCESS", "message": f"Agent {agent.agent_code} has been suspended and all active capabilities revoked."}

@router.post("/{id}/restore")
async def restore_agent(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if not has_permission(current_user.role, PERM_AGENT_RESUME):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to restore an agent"
        )

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot restore AI agent belonging to another organization"
        )

    agent.status = "NORMAL"
    cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()
    if cb:
        cb.state = "NORMAL"
        cb.restored_at = datetime.datetime.utcnow()

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="AGENT_RESTORED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="RESTORE_AGENT",
        resource=f"agent:{agent.agent_code}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "actor_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    await ws_manager.broadcast({
        "type": "AGENT_RESTORED",
        "agent_code": agent.agent_code,
        "name": agent.name,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {"status": "SUCCESS", "message": f"Agent {agent.agent_code} restored to NORMAL operational state."}


# ============================================================================
# AGENT MACHINE CREDENTIALS & CRYPTOGRAPHIC PASSPORT ENDPOINTS
# ============================================================================

from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service

@router.post("/{id}/credentials", response_model=schemas.AgentCredentialCreatedResponse)
async def create_agent_credential(
    id: str,
    req: schemas.AgentCredentialCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Issues a cryptographically secure machine credential for an AI agent.
    The plaintext token is returned ONLY ONCE. Only its SHA-256 hash is persisted.
    """
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot issue credentials for an agent in another organization"
        )

    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "DEVELOPER", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Admin, Developer, or Manager roles can generate agent credentials"
        )

    if agent.status in ("SUSPENDED", "CIRCUIT_BREAK"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate credentials for agent in {agent.status} state"
        )

    cred, plaintext = machine_auth_service.create_agent_credential(
        db=db,
        agent=agent,
        name=req.name,
        credential_type=req.credential_type,
        expires_in_days=req.expires_in_days
    )

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="AGENT_CREDENTIAL_CREATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CREATE_CREDENTIAL",
        resource=f"agent:{agent.agent_code}:credential:{cred.id}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "credential_id": str(cred.id),
            "credential_type": cred.credential_type,
            "key_prefix": cred.key_prefix,
            "actor_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    return schemas.AgentCredentialCreatedResponse(
        credential=schemas.AgentCredentialResponse.model_validate(cred),
        plaintext_token=plaintext,
        warning="Store this credential securely immediately. It will NEVER be shown again."
    )


@router.get("/{id}/credentials", response_model=list[schemas.AgentCredentialResponse])
def list_agent_credentials(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists credential metadata for an agent. Plaintext tokens and key hashes are NEVER returned.
    """
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view credentials of an agent belonging to another organization"
        )

    creds = db.query(models.AgentCredential).filter(
        models.AgentCredential.agent_id == agent.id
    ).order_by(models.AgentCredential.created_at.desc()).all()

    return [schemas.AgentCredentialResponse.model_validate(c) for c in creds]


@router.post("/{id}/credentials/{credential_id}/rotate", response_model=schemas.AgentCredentialCreatedResponse)
async def rotate_agent_credential(
    id: str,
    credential_id: str,
    req: schemas.AgentCredentialCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rotates an existing credential: atomically revokes the old credential and
    issues a new active machine credential.
    """
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot rotate credentials for an agent in another organization"
        )

    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "DEVELOPER", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to rotate agent credentials"
        )

    if agent.status in ("SUSPENDED", "CIRCUIT_BREAK"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot rotate credentials for agent in {agent.status} state"
        )

    try:
        new_cred, new_plaintext = machine_auth_service.rotate_agent_credential(
            db=db,
            agent=agent,
            old_credential_id=credential_id,
            name=req.name,
            expires_in_days=req.expires_in_days
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="AGENT_CREDENTIAL_ROTATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="ROTATE_CREDENTIAL",
        resource=f"agent:{agent.agent_code}:credential:{new_cred.id}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "old_credential_id": credential_id,
            "new_credential_id": str(new_cred.id),
            "actor_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    return schemas.AgentCredentialCreatedResponse(
        credential=schemas.AgentCredentialResponse.model_validate(new_cred),
        plaintext_token=new_plaintext,
        warning="Old credential revoked. Store this rotated credential immediately. It will NEVER be shown again."
    )


@router.delete("/{id}/credentials/{credential_id}")
async def revoke_agent_credential(
    id: str,
    credential_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revokes an active machine credential.
    """
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot revoke credentials for an agent in another organization"
        )

    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "DEVELOPER", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to revoke agent credentials"
        )

    success = machine_auth_service.revoke_agent_credential(
        db=db,
        agent_id=str(agent.id),
        credential_id=credential_id
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found for this agent")

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="AGENT_CREDENTIAL_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="REVOKE_CREDENTIAL",
        resource=f"agent:{agent.agent_code}:credential:{credential_id}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "credential_id": credential_id,
            "actor_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Credential {credential_id} successfully revoked."}


@router.post("/{id}/passport/sign")
async def sign_agent_passport(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Issues or re-signs the agent's cryptographic Ed25519 passport,
    incorporating current agent metadata and granted capabilities.
    """
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot sign passport for an agent in another organization"
        )

    passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent.id).first()
    if not passport:
        passport = models.AgentPassport(
            agent_id=agent.id,
            passport_number=f"AG-PASSPORT-{random.randint(100000, 999999)}",
            digital_signature="pending",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            verification_status="VERIFIED"
        )
        db.add(passport)

    # Fetch active capability names for this agent
    active_tokens = db.query(models.CapabilityToken).filter(
        models.CapabilityToken.agent_id == agent.id,
        models.CapabilityToken.status == "ACTIVE"
    ).all()
    caps = [t.capability_name for t in active_tokens]

    sig = passport_service.sign_passport(agent, passport, capabilities=caps)
    db.commit()
    db.refresh(passport)

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="PASSPORT_ISSUED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="SIGN_PASSPORT",
        resource=f"agent:{agent.agent_code}:passport:{passport.passport_number}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "passport_number": passport.passport_number,
            "algorithm": passport.algorithm,
            "key_id": passport.key_id,
            "actor_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "passport_number": passport.passport_number,
        "algorithm": passport.algorithm,
        "key_id": passport.key_id,
        "digital_signature": passport.digital_signature,
        "issued_at": passport.issued_at.isoformat(),
        "expires_at": passport.expires_at.isoformat(),
        "verification_status": passport.verification_status
    }


@router.get("/{id}/passport/verify", response_model=schemas.PassportVerifyResponse)
def verify_agent_passport(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authoritatively verifies the cryptographic Ed25519 digital signature,
    expiration date, and operational status of an agent's passport.
    """
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot verify passport of an agent belonging to another organization"
        )

    passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent.id).first()
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found for this agent")

    # Fetch active capabilities
    active_tokens = db.query(models.CapabilityToken).filter(
        models.CapabilityToken.agent_id == agent.id,
        models.CapabilityToken.status == "ACTIVE"
    ).all()
    caps = [t.capability_name for t in active_tokens]

    result = passport_service.verify_passport(passport, agent, capabilities=caps)
    db.commit()  # In case verify_passport updated expired status

    if not result["valid"]:
        audit = models.AuditLog(
            org_id=agent.org_id,
            event_type="PASSPORT_VERIFICATION_FAILED",
            actor_type="USER",
            actor_id=str(current_user.id),
            action="VERIFY_PASSPORT",
            resource=f"agent:{agent.agent_code}:passport:{passport.passport_number}",
            result="FAILURE",
            metadata_json={
                "agent_id": str(agent.id),
                "agent_code": agent.agent_code,
                "status": result["status"],
                "reason": result["reason"]
            }
        )
        db.add(audit)
        db.commit()

    return schemas.PassportVerifyResponse(
        valid=result["valid"],
        status=result["status"],
        verification_status=passport.verification_status,
        agent_code=agent.agent_code,
        passport_number=passport.passport_number,
        algorithm=getattr(passport, "algorithm", "Ed25519") or "Ed25519",
        key_id=getattr(passport, "key_id", passport_service.key_id) or passport_service.key_id,
        issued_at=passport.issued_at,
        expires_at=passport.expires_at,
        reason=result.get("reason")
    )


# ============================================================================
# AGENT PERMISSION MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/{id}/permissions", response_model=list[schemas.PermissionSchema])
def get_agent_permissions(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all granted runtime permissions for a specific agent.
    """
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cross-tenant access denied")

    return db.query(models.Permission).filter(models.Permission.agent_id == agent.id).all()


@router.post("/{id}/permissions", response_model=schemas.PermissionSchema, status_code=status.HTTP_201_CREATED)
def grant_agent_permission(
    id: str,
    req: schemas.PermissionCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Grants a runtime permission to a specific agent.
    """
    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "OPERATOR", "DEVELOPER", "SECURITY_ANALYST"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to grant agent permissions"
        )

    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cross-tenant access denied")

    perm = models.Permission(
        agent_id=agent.id,
        resource_type=req.resource_type.upper(),
        resource_name=req.resource_name,
        action=req.action.upper(),
        is_allowed=req.is_allowed,
        created_at=datetime.datetime.utcnow()
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="PERMISSION_GRANTED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="GRANT_PERMISSION",
        resource=f"agent:{agent.agent_code}:perm:{perm.id}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "resource_type": perm.resource_type,
            "resource_name": perm.resource_name,
            "action": perm.action,
            "is_allowed": perm.is_allowed,
            "permission_id": str(perm.id)
        }
    )
    db.add(audit)
    db.commit()

    return perm


@router.delete("/{id}/permissions/{permission_id}")
def revoke_agent_permission(
    id: str,
    permission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revokes a granted runtime permission from a specific agent.
    """
    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "OPERATOR", "DEVELOPER", "SECURITY_ANALYST"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to revoke agent permissions"
        )

    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cross-tenant access denied")

    perm = db.query(models.Permission).filter(
        models.Permission.id == permission_id,
        models.Permission.agent_id == agent.id
    ).first()

    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found for this agent")

    perm_id_str = str(perm.id)
    db.delete(perm)

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="PERMISSION_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="REVOKE_PERMISSION",
        resource=f"agent:{agent.agent_code}:perm:{perm_id_str}",
        result="SUCCESS",
        metadata_json={
            "agent_code": agent.agent_code,
            "permission_id": perm_id_str,
            "revoked_by": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Permission {perm_id_str} revoked successfully from agent {agent.agent_code}."}


