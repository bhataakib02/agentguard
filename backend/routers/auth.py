from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from core import security
from core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.TokenResponse)
def register_organization(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    # 1. Duplicate email check: Reject duplicate registrations to prevent account takeover
    existing_user = db.query(models.User).filter(models.User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in."
        )

    # 2. Transactional Organization Creation
    org = models.Organization(name=req.org_name)
    db.add(org)
    db.commit()
    db.refresh(org)

    # 3. Transactional User Creation (Strictly default to USER role)
    hashed_pw = security.get_password_hash(req.password) if req.password else None
    user = models.User(
        org_id=org.id,
        auth_user_id=req.auth_user_id,
        email=req.email,
        password_hash=hashed_pw,
        full_name=req.full_name,
        role="USER",
        department="General",
        status="ACTIVE"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 4. Session & Access Token Creation
    token = security.create_access_token(user.id, email=user.email, role=user.role)
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
def login(
    req: schemas.LoginRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )

    verified_user_id = None
    verified_email = None

    from config import settings
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        verified_user_id = payload.get("sub")
        verified_email = payload.get("email")
    except JWTError:
        from core.deps import verify_supabase_token
        verified = verify_supabase_token(token)
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or unverified authentication token"
            )
        verified_user_id, verified_email = verified

    # Validate that verified token matches the requested login account
    if verified_email and verified_email.lower() != req.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication token does not match requested email"
        )
    if verified_user_id and req.auth_user_id and str(verified_user_id) != str(req.auth_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication token does not match requested auth_user_id"
        )

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
            auth_user_id=req.auth_user_id or verified_user_id,
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

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Account status is {user.status}"
        )

    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    org_name = org.name if org else "AgentGuard Enterprise"

    user.last_login_at = security.utcnow()
    db.commit()

    session_token = security.create_access_token(user.id, email=user.email, role=user.role)
    session = models.Session(
        user_id=user.id,
        token=session_token,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)
    db.commit()

    return schemas.TokenResponse(
        access_token=session_token,
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
        org_name=org_name
    )

@router.post("/local-login", response_model=schemas.TokenResponse)
def local_login(req: schemas.LocalLoginRequest, db: Session = Depends(get_db)):
    """
    Fallback login for users who have a local password_hash but no Supabase Auth account.
    This covers demo/seeded users created directly in the database by seed scripts.
    """
    user = db.query(models.User).filter(models.User.email == req.email).first()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not security.verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or inactive"
        )

    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    org_name = org.name if org else "AgentGuard Enterprise"

    user.last_login_at = security.utcnow()
    db.commit()

    token = security.create_access_token(user.id, email=user.email, role=user.role)
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

@router.post("/logout")
def logout(
    authorization: str = Header(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        db_session = db.query(models.Session).filter(models.Session.token == token).first()
        if db_session:
            db_session.revoked = True
            db.commit()

    # Log audit entry
    audit = models.AuditLog(
        event_type="USER_LOGOUT",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="Logged out and revoked session",
        resource="sessions",
        result="SUCCESS",
        metadata_json={"user_id": str(current_user.id), "email": current_user.email}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": "Logged out successfully and session revoked"}

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
