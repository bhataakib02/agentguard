# type: ignore
import uuid
from typing import Optional, List, Dict, Any
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from core import security
from core.deps import get_current_user
from services.otp_service import (
    otp_service,
    encrypt_ephemeral_secret,
    decrypt_ephemeral_secret,
    PURPOSE_REGISTRATION,
    PURPOSE_PASSWORDLESS_LOGIN,
    PURPOSE_PASSWORD_RESET,
    RESEND_COOLDOWN_SECONDS
)
from services.email_service import email_service
from core.supabase_admin import supabase_admin
from config import settings

logger = logging.getLogger("agentguard.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _dispatch_otp_and_build_response(
    db: Session,
    *,
    clean_email: str,
    raw_code: str,
    purpose: str,
    ip_addr: str,
    event_type: str,
    action: str,
    actor_type: str = "SYSTEM",
    actor_id: str = "anonymous",
    org_id: Optional[str] = None,
    success_message: str = "A 6-digit verification code has been accepted for email delivery. Please check your inbox.",
) -> schemas.OtpActionResponse:
    """
    Sends an OTP email synchronously through the configured provider with correlation tracking,
    records a sanitized AuditLog entry, and raises a clear HTTP error if delivery fails—without
    consuming or invalidating the issued OTP challenge.
    """
    correlation_id = uuid.uuid4().hex[:12]
    email_result = email_service.send_otp_email(
        clean_email,
        raw_code,
        purpose,
        correlation_id=correlation_id,
    )

    accepted = bool(email_result.get("accepted"))
    stage = email_result.get("delivery_stage") or ("ACCEPTED_BY_PROVIDER" if accepted else "REJECTED_BY_PROVIDER")
    error_code = email_result.get("error_code")

    audit = models.AuditLog(
        org_id=org_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource="users",
        result=stage if accepted else (error_code or stage),
        metadata_json={
            "email": clean_email,
            "ip": ip_addr,
            "correlation_id": correlation_id,
            "provider": email_result.get("provider"),
            "delivery_stage": stage,
            "provider_message_id": email_result.get("id"),
            "http_status": email_result.get("http_status"),
            "error_code": error_code,
        },
    )
    db.add(audit)
    db.commit()

    if accepted:
        return schemas.OtpActionResponse(
            status="SUCCESS",
            message=success_message,
            cooldown_seconds=RESEND_COOLDOWN_SECONDS,
            delivery_status="ACCEPTED_FOR_SENDING",
            correlation_id=correlation_id,
            provider_message_id=email_result.get("id"),
        )

    if email_result.get("status") == "EMAIL_PROVIDER_NOT_CONFIGURED":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Email provider configuration is missing. Verification email could not be sent (ref: {correlation_id}).",
        )

    if stage == "TRANSIENT_FAILURE":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Email delivery could not be confirmed due to a temporary mail service or network error. "
                f"Your verification code remains valid; please wait for the cooldown or try resending (ref: {correlation_id})."
            ),
        )

    if error_code in ("RECIPIENT_RESTRICTED", "UNVERIFIED_SENDER_DOMAIN"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Email sending failed: Sender domain is not verified for external recipients "
                f"(ref: {correlation_id})."
            ),
        )

    if error_code == "UNVERIFIED_SENDER":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Email sending failed: Sender address or domain is not verified for external recipients "
                f"(ref: {correlation_id})."
            ),
        )

    if error_code == "RECIPIENT_REJECTED":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email sending failed: Recipient address was rejected by the mail provider (ref: {correlation_id}).",
        )

    if error_code == "INVALID_API_KEY":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email sending failed: Email provider API key was rejected (ref: {correlation_id}).",
        )

    if error_code == "INVALID_SENDER":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email sending failed: Configured sender email address is invalid (ref: {correlation_id}).",
        )

    if error_code == "MALFORMED_RESPONSE":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Email delivery could not be confirmed due to an unexpected response from the mail provider. "
                f"Your verification code remains valid; please check your inbox or retry after cooldown (ref: {correlation_id})."
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Email sending failed. Please verify your email address or try again later (ref: {correlation_id}).",
    )


# ============================================================================
# FLOW 1: REGISTRATION WITH EMAIL OTP
# ============================================================================

@router.post("/register/request-otp", response_model=schemas.OtpActionResponse)
def register_request_otp(
    req: schemas.RegisterOtpRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Step 1 of Registration: Request a 6-digit email OTP.
    - Validates inputs.
    - Prevents account enumeration by returning generic response if account already exists.
    - Enforces resend cooldown and rate limits.
    - Stores pending registration state securely (password_hash and authenticated ephemeral ciphertext).
    - Dispatches 6-digit OTP code asynchronously via configured email provider.
    """
    clean_email = otp_service.normalize_email(req.email)
    ip_addr = get_client_ip(request)

    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email address is required"
        )

    if not req.password or len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )

    if not req.full_name or not req.full_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name is required"
        )

    # 1. Rate Limit Check (Shared per-IP and per-email)
    is_limited, reason = otp_service.check_rate_limits(db, clean_email, ip_addr)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason
        )

    # 2. Anti-Enumeration & Duplicate Check:
    # If account exists and is ACTIVE, record probe for IP rate limiting and return generic response
    existing_user = db.query(models.User).filter(models.User.email == clean_email).first()
    if existing_user and existing_user.status == "ACTIVE":
        otp_service.record_ip_probe(db, ip_addr, clean_email, PURPOSE_REGISTRATION)
        audit = models.AuditLog(
            event_type="USER_REGISTER_OTP_REQUESTED",
            actor_type="SYSTEM",
            actor_id="anonymous",
            action="REQUEST_REGISTRATION_OTP",
            resource="users",
            result="IGNORED_DUPLICATE",
            metadata_json={"email": clean_email, "ip": ip_addr}
        )
        db.add(audit)
        db.commit()
        return schemas.OtpActionResponse(
            status="SUCCESS",
            message="If this email address is eligible, a 6-digit verification code has been sent.",
            cooldown_seconds=RESEND_COOLDOWN_SECONDS
        )

    # 3. Resend Cooldown Check
    is_cd, remaining = otp_service.check_resend_cooldown(db, clean_email, PURPOSE_REGISTRATION)
    if is_cd:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting a new verification code."
        )

    # 4. Hash password and encrypt ephemeral credential for safe Supabase Auth sync upon OTP verification
    hashed_pw = security.get_password_hash(req.password)
    encrypted_pw = encrypt_ephemeral_secret(req.password, clean_email)
    org_title = req.org_name.strip() if req.org_name and req.org_name.strip() else f"{req.full_name.strip()}'s Organization"

    challenge_meta = {
        "full_name": req.full_name.strip(),
        "org_name": org_title,
        "password_hash": hashed_pw,
        "encrypted_password": encrypted_pw
    }

    # 5. Issue cryptographic challenge (HMAC-stored, expires in 10 minutes)
    challenge, raw_code = otp_service.issue_challenge(
        db,
        clean_email,
        PURPOSE_REGISTRATION,
        ip_address=ip_addr,
        metadata_json=challenge_meta
    )

    # 6. Dispatch OTP email synchronously with delivery verification and audit logging
    return _dispatch_otp_and_build_response(
        db,
        clean_email=clean_email,
        raw_code=raw_code,
        purpose=PURPOSE_REGISTRATION,
        ip_addr=ip_addr,
        event_type="USER_REGISTER_OTP_REQUESTED",
        action="REQUEST_REGISTRATION_OTP",
        success_message="A 6-digit verification code has been accepted for email delivery. Please check your inbox.",
    )


@router.post("/register/verify-otp", response_model=schemas.TokenResponse)
def register_verify_otp(
    req: schemas.RegisterVerifyOtpRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 2 of Registration: Verify the 6-digit OTP and complete account creation.
    - Atomically verifies challenge with attempt limit check.
    - Creates Organization and User with safe default role 'USER'.
    - Synchronizes with Supabase Auth when configured.
    - Issues authenticated session and access token.
    """
    clean_email = otp_service.normalize_email(req.email)
    ip_addr = get_client_ip(request)

    if not req.otp or len(req.otp.strip()) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code must be exactly 6 digits."
        )

    # 1. Verification without premature consumption (Enforces max 5 attempts & 10-minute expiration)
    # The challenge is consumed ONLY after authoritative account creation succeeds.
    valid, err_msg, challenge = otp_service.verify_challenge(
        db, clean_email, PURPOSE_REGISTRATION, req.otp, consume=False
    )
    if not valid or not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Invalid or expired verification code."
        )

    # 2. Check if active user already exists
    existing_user = db.query(models.User).filter(models.User.email == clean_email).first()
    if existing_user and existing_user.status == "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in."
        )

    meta = challenge.metadata_json or {}
    full_name = meta.get("full_name") or clean_email.split("@")[0].capitalize()
    org_name = meta.get("org_name") or f"{full_name}'s Organization"
    password_hash = meta.get("password_hash")

    # 3. Safe Supabase Auth Synchronization (Fail-Closed)
    auth_user_id = None
    if supabase_admin.is_configured:
        try:
            chosen_password = decrypt_ephemeral_secret(meta.get("encrypted_password"), clean_email) if meta.get("encrypted_password") else None
            auth_user_id = supabase_admin.create_user(
                clean_email,
                password=chosen_password,
                full_name=full_name,
                email_confirm=True
            )
        except Exception as e:
            logger.error(f"[Registration] Supabase Auth creation error: {e}")
            auth_user_id = None

        if not auth_user_id:
            # Registration MUST fail closed — do NOT create active local user, do NOT consume OTP
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to complete account registration with identity provider. Please try again."
            )
    elif settings.ENVIRONMENT == "production":
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider configuration is required for registration in production."
        )

    # 4. Transactional Organization & User Creation / Activation
    if existing_user:
        user = existing_user
        setattr(user, "auth_user_id", auth_user_id)
        setattr(user, "status", "ACTIVE")
        if password_hash:
            setattr(user, "password_hash", password_hash)
        if full_name:
            setattr(user, "full_name", full_name)
        org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
        if not org:
            org = models.Organization(name=org_name)
            db.add(org)
            db.flush()
            setattr(user, "org_id", org.id)
    else:
        org = models.Organization(name=org_name)
        db.add(org)
        db.flush()

        user = models.User(
            org_id=org.id,
            auth_user_id=auth_user_id,
            email=clean_email,
            password_hash=password_hash,
            full_name=full_name,
            role="USER",
            department="General",
            status="ACTIVE"
        )
        db.add(user)
        db.flush()

    # 5. Atomically consume challenge and scrub ephemeral credentials
    otp_service.consume_challenge(db, challenge, scrub=True)

    # 6. Session Creation
    token = security.create_access_token(str(user.id), email=str(user.email), role=str(user.role))
    session = models.Session(
        user_id=user.id,
        token=token,
        ip_address=ip_addr,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)

    # 7. Audit log event
    audit = models.AuditLog(
        org_id=user.org_id,
        event_type="USER_REGISTER_VERIFIED",
        actor_type="USER",
        actor_id=str(user.id),
        action="VERIFY_REGISTRATION_OTP",
        resource=f"users:{user.id}",
        result="SUCCESS",
        metadata_json={"email": user.email, "ip": ip_addr, "role": user.role}
    )
    db.add(audit)
    db.commit()

    return schemas.TokenResponse(
        access_token=token,
        user_id=str(user.id),
        auth_user_id=str(user.auth_user_id) if user.auth_user_id else None,
        role=str(user.role),
        full_name=str(user.full_name),
        email=str(user.email),
        org_name=str(org.name)
    )


# ============================================================================
# FLOW 3: LOGIN METHOD B: PASSWORDLESS EMAIL OTP
# ============================================================================

@router.post("/login/request-otp", response_model=schemas.OtpActionResponse)
def login_request_otp(
    req: schemas.LoginOtpRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Step 1 of Passwordless Login: Request a 6-digit login OTP.
    - User enters email without password.
    - Anti-enumeration: Returns generic response regardless of whether account exists.
    - Only issues OTP to eligible ACTIVE accounts.
    - Enforces resend cooldown and distributed rate limiting.
    """
    clean_email = otp_service.normalize_email(req.email)
    ip_addr = get_client_ip(request)

    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email address is required"
        )

    # 1. Rate Limit Check (Shared per-IP and per-email)
    is_limited, reason = otp_service.check_rate_limits(db, clean_email, ip_addr)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason
        )

    # 2. Anti-Enumeration & Eligibility Check:
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user or user.status != "ACTIVE":
        otp_service.record_ip_probe(db, ip_addr, clean_email, PURPOSE_PASSWORDLESS_LOGIN)
        audit = models.AuditLog(
            event_type="USER_LOGIN_OTP_REQUESTED",
            actor_type="SYSTEM",
            actor_id="anonymous",
            action="REQUEST_LOGIN_OTP",
            resource="users",
            result="IGNORED_INELIGIBLE",
            metadata_json={"email": clean_email, "ip": ip_addr}
        )
        db.add(audit)
        db.commit()
        return schemas.OtpActionResponse(
            status="SUCCESS",
            message="If the account exists and is eligible, a 6-digit verification code has been sent.",
            cooldown_seconds=RESEND_COOLDOWN_SECONDS
        )

    # 3. Resend Cooldown Check
    is_cd, remaining = otp_service.check_resend_cooldown(db, clean_email, PURPOSE_PASSWORDLESS_LOGIN)
    if is_cd:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting a new login code."
        )

    # 4. Issue challenge (HMAC-stored, 10 min expiry)
    challenge, raw_code = otp_service.issue_challenge(
        db,
        clean_email,
        PURPOSE_PASSWORDLESS_LOGIN,
        ip_address=ip_addr
    )

    # 5. Dispatch OTP email synchronously with delivery verification and audit logging
    return _dispatch_otp_and_build_response(
        db,
        clean_email=clean_email,
        raw_code=raw_code,
        purpose=PURPOSE_PASSWORDLESS_LOGIN,
        ip_addr=ip_addr,
        event_type="USER_LOGIN_OTP_REQUESTED",
        action="REQUEST_LOGIN_OTP",
        actor_type="USER",
        actor_id=str(user.id),
        org_id=str(user.org_id) if user.org_id else None,
        success_message="A 6-digit verification code has been accepted for email delivery. Please check your inbox.",
    )


@router.post("/login/verify-otp", response_model=schemas.TokenResponse)
def login_verify_otp(
    req: schemas.LoginVerifyOtpRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 2 of Passwordless Login: Verify 6-digit OTP and establish session.
    - Atomically verifies challenge with attempt limit check.
    - Validates account eligibility and status.
    - Creates server-side session and issues access token.
    """
    clean_email = otp_service.normalize_email(req.email)
    ip_addr = get_client_ip(request)

    if not req.otp or len(req.otp.strip()) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code must be exactly 6 digits."
        )

    # 1. Atomic Verification
    valid, err_msg, challenge = otp_service.verify_challenge(
        db, clean_email, PURPOSE_PASSWORDLESS_LOGIN, req.otp
    )
    if not valid or not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Invalid or expired verification code."
        )

    # 2. Account Eligibility Check
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found."
        )

    if str(user.status) != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Account status is {user.status}"
        )

    # 3. Update Last Login
    setattr(user, "last_login_at", security.utcnow())
    db.commit()

    # 4. Create Session
    session_token = security.create_access_token(str(user.id), email=str(user.email), role=str(user.role))
    session = models.Session(
        user_id=user.id,
        token=session_token,
        ip_address=ip_addr,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)

    # 5. Audit Log
    audit = models.AuditLog(
        org_id=user.org_id,
        event_type="USER_LOGIN_OTP_SUCCESS",
        actor_type="USER",
        actor_id=str(user.id),
        action="LOGIN_PASSWORDLESS_OTP",
        resource="sessions",
        result="SUCCESS",
        metadata_json={"email": user.email, "ip": ip_addr}
    )
    db.add(audit)
    db.commit()

    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    org_name = str(org.name) if org and org.name else "AgentGuard Enterprise"

    return schemas.TokenResponse(
        access_token=session_token,
        user_id=str(user.id),
        auth_user_id=str(user.auth_user_id) if user.auth_user_id else None,
        role=str(user.role),
        full_name=str(user.full_name),
        email=str(user.email),
        org_name=org_name
    )


# ============================================================================
# FLOW 4: FORGOT PASSWORD / PASSWORD RECOVERY WITH OTP
# ============================================================================

@router.post("/forgot-password/request-otp", response_model=schemas.OtpActionResponse)
def forgot_password_request_otp(
    req: schemas.ForgotPasswordOtpRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Step 1 of Password Reset: Request a 6-digit recovery OTP.
    - Anti-enumeration: Returns generic response regardless of whether account exists.
    - Issues recovery OTP only to eligible active accounts.
    - Bound to PASSWORD_RESET purpose with 10-minute validity.
    """
    clean_email = otp_service.normalize_email(req.email)
    ip_addr = get_client_ip(request)

    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email address is required"
        )

    # 1. Rate Limit Check (Shared per-IP and per-email)
    is_limited, reason = otp_service.check_rate_limits(db, clean_email, ip_addr)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason
        )

    # 2. Anti-Enumeration & User Check:
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user or user.status != "ACTIVE":
        otp_service.record_ip_probe(db, ip_addr, clean_email, PURPOSE_PASSWORD_RESET)
        audit = models.AuditLog(
            event_type="PASSWORD_RESET_OTP_REQUESTED",
            actor_type="SYSTEM",
            actor_id="anonymous",
            action="REQUEST_PASSWORD_RESET_OTP",
            resource="users",
            result="IGNORED_INELIGIBLE",
            metadata_json={"email": clean_email, "ip": ip_addr}
        )
        db.add(audit)
        db.commit()
        return schemas.OtpActionResponse(
            status="SUCCESS",
            message="If the account exists and is eligible, a 6-digit recovery code has been sent.",
            cooldown_seconds=RESEND_COOLDOWN_SECONDS
        )

    # 3. Resend Cooldown Check
    is_cd, remaining = otp_service.check_resend_cooldown(db, clean_email, PURPOSE_PASSWORD_RESET)
    if is_cd:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting a new recovery code."
        )

    # 4. Issue challenge (HMAC-stored, 10 min expiry)
    challenge, raw_code = otp_service.issue_challenge(
        db,
        clean_email,
        PURPOSE_PASSWORD_RESET,
        ip_address=ip_addr
    )

    # 5. Dispatch OTP email synchronously with delivery verification and audit logging
    return _dispatch_otp_and_build_response(
        db,
        clean_email=clean_email,
        raw_code=raw_code,
        purpose=PURPOSE_PASSWORD_RESET,
        ip_addr=ip_addr,
        event_type="PASSWORD_RESET_OTP_REQUESTED",
        action="REQUEST_PASSWORD_RESET_OTP",
        actor_type="USER",
        actor_id=str(user.id),
        org_id=str(user.org_id) if user.org_id else None,
        success_message="A 6-digit recovery code has been accepted for email delivery. Please check your inbox.",
    )


@router.post("/forgot-password/verify-otp", response_model=schemas.OtpActionResponse)
def forgot_password_verify_otp(
    req: schemas.ForgotPasswordVerifyOtpRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2 of Password Reset: Verify recovery OTP and issue short-lived reset ticket.
    """
    clean_email = otp_service.normalize_email(req.email)

    if not req.otp or len(req.otp.strip()) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code must be exactly 6 digits."
        )

    valid, err_msg, challenge = otp_service.verify_challenge(
        db, clean_email, PURPOSE_PASSWORD_RESET, req.otp
    )
    if not valid or not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Invalid or expired recovery code."
        )

    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request.")

    ticket = otp_service.create_reset_ticket(str(user.id), str(user.email))

    audit = models.AuditLog(
        org_id=user.org_id,
        event_type="PASSWORD_RESET_OTP_VERIFIED",
        actor_type="USER",
        actor_id=str(user.id),
        action="VERIFY_PASSWORD_RESET_OTP",
        resource="users",
        result="SUCCESS",
        metadata_json={"email": user.email}
    )
    db.add(audit)
    db.commit()

    return schemas.OtpActionResponse(
        status="SUCCESS",
        message="Recovery code verified successfully. Please enter your new password.",
        reset_ticket=ticket
    )


@router.post("/forgot-password/reset", response_model=schemas.OtpActionResponse)
def forgot_password_reset(
    req: schemas.ForgotPasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 3 of Password Reset: Set new password and revoke all existing sessions.
    - Requires either a verified reset_ticket or direct valid OTP.
    - Updates local password_hash and Supabase Auth password when configured.
    - Revokes ALL existing active sessions for this user.
    """
    clean_email = otp_service.normalize_email(req.email)
    ip_addr = get_client_ip(request)

    if not req.new_password or len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )

    user = None
    if req.reset_ticket:
        valid, err_msg, user_id = otp_service.verify_reset_ticket(db, req.reset_ticket, clean_email, consume=True)
        if not valid or not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg or "Invalid reset ticket.")
        user = db.query(models.User).filter(models.User.id == user_id).first()
    elif req.otp:
        valid, err_msg, challenge = otp_service.verify_challenge(
            db, clean_email, PURPOSE_PASSWORD_RESET, req.otp, consume=True
        )
        if not valid or not challenge:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg or "Invalid recovery code.")
        user = db.query(models.User).filter(models.User.email == clean_email).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either reset_ticket or otp is required to reset password."
        )

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account not found.")

    # 1. Update Supabase Auth Password first for Supabase-backed users
    is_supabase_user = bool(user.auth_user_id and supabase_admin.is_configured)
    if is_supabase_user:
        try:
            sb_success = supabase_admin.update_user_password(str(user.auth_user_id), req.new_password)
        except Exception as e:
            logger.error(f"[PasswordReset] Supabase Auth password update error: {e}")
            sb_success = False

        if not sb_success:
            # DO NOT commit local password hash update if authoritative update failed
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update password with identity provider. Please try again."
            )
        # Commit local password hash ONLY after authoritative provider has succeeded
        setattr(user, "password_hash", security.get_password_hash(req.new_password))
    else:
        # Local-only account: verify environment policy allows local auth
        if settings.ENVIRONMENT == "production" and not getattr(settings, "ALLOW_LOCAL_LOGIN", False):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password updates for local accounts are disabled in production."
            )
        setattr(user, "password_hash", security.get_password_hash(req.new_password))

    # 3. Session Revocation Policy: Revoke all active sessions for this user
    revoked_count = db.query(models.Session).filter(
        models.Session.user_id == user.id,
        models.Session.revoked == False
    ).update({"revoked": True}, synchronize_session=False)

    # 4. Audit Log
    audit = models.AuditLog(
        org_id=user.org_id,
        event_type="PASSWORD_RESET_COMPLETED",
        actor_type="USER",
        actor_id=str(user.id),
        action="RESET_PASSWORD",
        resource=f"users:{user.id}",
        result="SUCCESS",
        metadata_json={
            "email": user.email,
            "ip": ip_addr,
            "revoked_sessions_count": revoked_count
        }
    )
    db.add(audit)

    try:
        db.commit()
    except Exception as commit_err:
        logger.error(f"[PasswordReset] Local database commit failed after Supabase update: {commit_err}")
        db.rollback()
        # Reconciliation: Authoritative update already succeeded in Supabase.
        # Retry session revocation in a focused transaction to ensure existing sessions cannot persist.
        try:
            db.query(models.Session).filter(
                models.Session.user_id == user.id,
                models.Session.revoked == False
            ).update({"revoked": True}, synchronize_session=False)
            db.commit()
        except Exception as retry_err:
            logger.warning(f"[PasswordReset] Session revocation retry failed: {retry_err}")
            db.rollback()

        if is_supabase_user:
            # For Supabase-backed users, authoritative credential update has already succeeded in Supabase.
            # Stale local credentials cannot be used (local-login strictly forbids auth_user_id accounts).
            # Return success guidance to user so they proceed to log in with their new password.
            return schemas.OtpActionResponse(
                status="SUCCESS",
                message="Password has been reset successfully with the identity provider. All active sessions have been revoked. Please log in with your new password."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist password update. Please try again."
        )

    return schemas.OtpActionResponse(
        status="SUCCESS",
        message="Password has been reset successfully. All active sessions have been revoked. Please log in with your new password."
    )


# ============================================================================
# LEGACY & DIRECT REGISTRATION
# ============================================================================

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

    # 3. Synchronize with Supabase Auth if configured and not already provided
    auth_user_id = req.auth_user_id
    if not auth_user_id and supabase_admin.is_configured and req.password:
        try:
            auth_user_id = supabase_admin.create_user(
                req.email,
                password=req.password,
                full_name=req.full_name,
                email_confirm=True
            )
        except Exception as e:
            logger.error(f"[LegacyRegister] Supabase Admin sync error: {e}")
            auth_user_id = None

        if not auth_user_id:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Identity provider synchronization failed. Registration cannot complete without authoritative identity."
            )
    elif not auth_user_id and settings.ENVIRONMENT == "production":
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider configuration is required for registration in production."
        )

    # 4. Transactional User Creation (Strictly default to safe USER role)
    hashed_pw = security.get_password_hash(req.password) if req.password else None
    user = models.User(
        org_id=org.id,
        auth_user_id=auth_user_id,
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

    # 5. Session & Access Token Creation
    token = security.create_access_token(str(user.id), email=str(user.email), role=str(user.role))
    session = models.Session(
        user_id=user.id,
        token=token,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)
    db.commit()

    return schemas.TokenResponse(
        access_token=token,
        user_id=str(user.id),
        auth_user_id=str(user.auth_user_id) if user.auth_user_id else None,
        role=str(user.role),
        full_name=str(user.full_name),
        email=str(user.email),
        org_name=str(org.name)
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
        tok_type = payload.get("token_type") or payload.get("type")
        if tok_type in ("machine", "ws_ticket") or payload.get("agent_id") or payload.get("ticket_id") or payload.get("credential_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Forbidden: {tok_type or 'Machine'} token cannot be used for human user login."
            )
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
    if not verified_email:
        token_user = None
        if verified_user_id:
            token_user = db.query(models.User).filter(
                (models.User.id == verified_user_id) | (models.User.auth_user_id == verified_user_id)
            ).first()
        if not token_user or token_user.email.lower() != req.email.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token does not match requested user account"
            )
    if verified_user_id and req.auth_user_id and str(verified_user_id) != req.auth_user_id:
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
        setattr(user, "auth_user_id", req.auth_user_id)
        db.commit()

    if str(user.status) != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Account status is {user.status}"
        )

    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    org_name = str(org.name) if org and org.name else "AgentGuard Enterprise"

    setattr(user, "last_login_at", security.utcnow())
    db.commit()

    session_token = security.create_access_token(str(user.id), email=str(user.email), role=str(user.role))
    session = models.Session(
        user_id=user.id,
        token=session_token,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)
    db.commit()

    return schemas.TokenResponse(
        access_token=session_token,
        user_id=str(user.id),
        auth_user_id=str(user.auth_user_id) if user.auth_user_id else None,
        role=str(user.role),
        full_name=str(user.full_name),
        email=str(user.email),
        org_name=org_name
    )

@router.post("/local-login", response_model=schemas.TokenResponse)
def local_login(req: schemas.LocalLoginRequest, db: Session = Depends(get_db)):
    """
    Fallback login for explicitly supported local-only or development accounts.
    - Prohibited in production unless explicitly enabled via environment configuration.
    - Strictly rejects accounts with a Supabase identity when Supabase is configured.
    """
    is_production = (settings.ENVIRONMENT == "production")
    allow_local = getattr(settings, "ALLOW_LOCAL_LOGIN", False)
    if is_production and not allow_local:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local password authentication is disabled in this environment. Please authenticate via the enterprise identity provider."
        )

    clean_email = otp_service.normalize_email(req.email)
    user = db.query(models.User).filter(models.User.email == clean_email).first()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Supabase Auth bypass protection: accounts managed by Supabase cannot use local-login fallback
    if user.auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local login is not permitted for accounts managed by Supabase Auth. Please sign in with Supabase."
        )

    if not security.verify_password(req.password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if str(user.status) != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or inactive"
        )

    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    org_name = str(org.name) if org and org.name else "AgentGuard Enterprise"

    setattr(user, "last_login_at", security.utcnow())
    db.commit()

    token = security.create_access_token(str(user.id), email=str(user.email), role=str(user.role))
    session = models.Session(
        user_id=user.id,
        token=token,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)
    db.commit()

    return schemas.TokenResponse(
        access_token=token,
        user_id=str(user.id),
        auth_user_id=str(user.auth_user_id) if user.auth_user_id else None,
        role=str(user.role),
        full_name=str(user.full_name),
        email=str(user.email),
        org_name=org_name
    )

@router.get("/me", response_model=schemas.UserSchema)
def get_me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.org_id).first()
    org_name: str = str(getattr(org, "name", None)) if org and getattr(org, "name", None) else (
        "AgentGuard Control Plane" if str(current_user.role) == "SUPER_ADMIN" else "AgentGuard Enterprise"
    )

    return schemas.UserSchema(
        id=str(current_user.id),
        auth_user_id=str(current_user.auth_user_id) if current_user.auth_user_id else None,
        org_id=str(current_user.org_id) if current_user.org_id else None,
        email=str(current_user.email),
        full_name=str(current_user.full_name),
        role=str(current_user.role),
        department=str(current_user.department) if current_user.department else None,
        status=str(current_user.status),
        created_at=getattr(current_user, "created_at") or security.utcnow(),
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
            setattr(db_session, "revoked", True)
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

@router.post("/ws-ticket")
def issue_ws_ticket(current_user: models.User = Depends(get_current_user)):
    """
    Issues a short-lived (60s), single-use authenticated ticket for WebSocket connection.
    Prevents long-lived bearer tokens from persisting in WebSocket query strings or logs.
    """
    from ws_manager import ws_ticket_manager
    try:
        ticket = ws_ticket_manager.issue_ticket(
            user_id=str(current_user.id),
            org_id=str(current_user.org_id) if current_user.org_id else None,
            role=str(current_user.role),
            email=str(current_user.email) if current_user.email else None
        )
    except RuntimeError as e:
        logger.error(f"[WebSocket Ticket] Issuance blocked: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed session storage unavailable in production environment"
        )
    return {"ticket": ticket, "expires_in": 60, "token_type": "ws_ticket"}

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


# ============================================================================
# PHASE 5: INVITATION ACCEPTANCE & VERIFICATION
# ============================================================================

class AcceptInvitationRequest(BaseModel):
    full_name: str
    password: Optional[str] = None


def _is_token_expired(dt):
    if not dt:
        return False
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    if getattr(dt, 'tzinfo', None) is not None:
        dt = dt.replace(tzinfo=None)
    return dt < now


@router.get("/invitations/{token}/verify")
def verify_invitation(token: str, db: Session = Depends(get_db)):
    """Validates an invitation token without consuming it."""
    import hashlib
    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    inv = db.query(models.UserInvitation).filter(models.UserInvitation.token_hash == token_hash).first()
    if not inv:
        return {"valid": False, "error": "Invalid invitation token"}

    if str(inv.status) != "PENDING":
        return {"valid": False, "error": f"Invitation is no longer valid (status: {inv.status})"}

    if _is_token_expired(inv.expires_at):
        setattr(inv, "status", "EXPIRED")
        db.commit()
        return {"valid": False, "error": "Invitation token has expired"}

    org = db.query(models.Organization).filter(models.Organization.id == inv.org_id).first()
    return {
        "valid": True,
        "email": inv.email,
        "role": inv.role,
        "org_name": org.name if org else "AgentGuard Enterprise",
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None
    }


@router.post("/invitations/{token}/accept", response_model=schemas.TokenResponse)
def accept_invitation(
    token: str,
    req: AcceptInvitationRequest,
    db: Session = Depends(get_db)
):
    """
    Accepts an organization invitation. Validates token hash, enforces one-time use,
    activates/creates user in organization with assigned role, and returns access token.
    """
    import hashlib
    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    inv = db.query(models.UserInvitation).filter(models.UserInvitation.token_hash == token_hash).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid or non-existent invitation token")

    if str(inv.status) != "PENDING":
        raise HTTPException(status_code=400, detail=f"Invitation has already been {inv.status.lower()}")

    if _is_token_expired(inv.expires_at):
        setattr(inv, "status", "EXPIRED")
        db.commit()
        raise HTTPException(status_code=400, detail="Invitation token has expired")

    org = db.query(models.Organization).filter(models.Organization.id == inv.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization associated with invitation no longer exists")

    # Find or create user
    user = db.query(models.User).filter(models.User.email == inv.email).first()
    if user:
        setattr(user, "org_id", inv.org_id)
        setattr(user, "role", inv.role)
        setattr(user, "status", "ACTIVE")
        if req.full_name:
            setattr(user, "full_name", req.full_name)
        if req.password:
            setattr(user, "password_hash", security.get_password_hash(req.password))
    else:
        hashed_pw = security.get_password_hash(req.password) if req.password else None
        user = models.User(
            org_id=inv.org_id,
            email=inv.email,
            password_hash=hashed_pw,
            full_name=req.full_name,
            role=inv.role,
            department="General",
            status="ACTIVE"
        )
        db.add(user)

    # Invalidate invitation (ONE-TIME USE)
    setattr(inv, "status", "ACCEPTED")
    setattr(inv, "accepted_at", security.utcnow())

    db.commit()
    db.refresh(user)

    # Issue access token
    access_token = security.create_access_token(str(user.id), email=str(user.email), role=str(user.role))
    session = models.Session(
        user_id=user.id,
        token=access_token,
        expires_at=security.utcnow() + security.timedelta(hours=24)
    )
    db.add(session)

    # Transactional audit
    audit = models.AuditLog(
        org_id=user.org_id,
        event_type="INVITATION_ACCEPTED",
        actor_type="USER",
        actor_id=str(user.id),
        action="ACCEPT_INVITATION",
        resource=f"invitation:{inv.id}",
        result="SUCCESS",
        metadata_json={
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "org_id": str(user.org_id)
        }
    )
    db.add(audit)
    db.commit()

    return schemas.TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        auth_user_id=str(user.auth_user_id) if user.auth_user_id else None,
        role=str(user.role),
        full_name=str(user.full_name),
        email=str(user.email),
        org_name=str(org.name)
    )

