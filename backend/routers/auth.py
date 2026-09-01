from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from core import security
from core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.TokenResponse)
def register_organization(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    # 1. Duplicate email check
    existing_user = db.query(models.User).filter(models.User.email == req.email).first()
    if existing_user:
        if req.auth_user_id and not existing_user.auth_user_id:
            existing_user.auth_user_id = req.auth_user_id
            db.commit()

        org = db.query(models.Organization).filter(models.Organization.id == existing_user.org_id).first()
        org_name = org.name if org else req.org_name

        token = security.create_access_token(existing_user.id)
        return schemas.TokenResponse(
            access_token=token,
            user_id=existing_user.id,
            auth_user_id=existing_user.auth_user_id,
            role=existing_user.role,
            full_name=existing_user.full_name,
            email=existing_user.email,
            org_name=org_name
        )

    # 2. Transactional Organization Creation
    org = models.Organization(name=req.org_name)
    db.add(org)
    db.commit()
    db.refresh(org)

    # 3. Transactional User Creation
    hashed_pw = security.get_password_hash(req.password) if req.password else None
    user = models.User(
        org_id=org.id,
        auth_user_id=req.auth_user_id,
        email=req.email,
        password_hash=hashed_pw,
        full_name=req.full_name,
        role="USER",
        department="General"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 4. Session & Access Token Creation
    token = security.create_access_token(user.id)
    session = models.Session(
        user_id=user.id,
        token=token,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)
    db.commit()

    return schemas.TokenResponse(
        access_token=token,
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
        org_name=org.name
    )

@router.post("/login", response_model=schemas.TokenResponse)
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()

    if not user and req.auth_user_id:
        user = db.query(models.User).filter(models.User.auth_user_id == req.auth_user_id).first()

    if not user:
        org_name = f"{req.email.split('@')[0].capitalize()} Org"
        org = models.Organization(name=org_name)
        db.add(org)
        db.commit()
        db.refresh(org)

        user = models.User(
            org_id=org.id,
            auth_user_id=req.auth_user_id,
            email=req.email,
            full_name=req.email.split('@')[0].replace('.', ' ').title(),
            role="USER",
            department="General"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif req.auth_user_id and not user.auth_user_id:
        user.auth_user_id = req.auth_user_id
        db.commit()

    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    org_name = org.name if org else "AgentGuard Enterprise"

    user.last_login_at = security.utcnow()
    db.commit()

    token = security.create_access_token(user.id)
    session = models.Session(
        user_id=user.id,
        token=token,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)
    db.commit()

    return schemas.TokenResponse(
        access_token=token,
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
        org_name=org_name
    )

@router.get("/me", response_model=schemas.UserSchema)
def get_me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.org_id).first()
    org_name = org.name if org else ("AgentGuard Control Plane" if current_user.role == "SUPER_ADMIN" else "AgentGuard Enterprise")

    return schemas.UserSchema(
        id=current_user.id,
        auth_user_id=current_user.auth_user_id,
        org_id=current_user.org_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        status=current_user.status,
        created_at=current_user.created_at,
        org_name=org_name
    )

@router.post("/resend-verification")
def resend_verification_email(req: dict, db: Session = Depends(get_db)):
    email = req.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = db.query(models.User).filter(models.User.email == email).first()

    # Write audit log record
    audit = models.AuditLog(
        event_type="EMAIL_VERIFICATION_RESENT",
        actor_type="USER",
        actor_id=str(user.id) if user else "anonymous",
        action="Requested email verification link resend",
        resource="users",
        result="SUCCESS",
        metadata_json={"email": email}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Verification email request recorded for {email}"}
