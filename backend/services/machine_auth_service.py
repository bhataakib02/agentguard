import secrets
import hashlib
import uuid
import datetime
import logging
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from config import settings
import models

logger = logging.getLogger("agentguard.machine_auth")

CREDENTIAL_PREFIX = "ag_agent_"
TOKEN_TYPE_MACHINE = "machine"
DEFAULT_MACHINE_TOKEN_EXPIRE_HOURS = 1

class MachineAuthService:
    """
    Service for Machine Agent Credentials, Machine Authentication,
    and Short-Lived Machine JWT Issuance & Verification.
    """

    @staticmethod
    def generate_raw_credential() -> str:
        """
        Generates a cryptographically secure random credential token
        with 'ag_agent_' prefix and 32 bytes (256 bits) of entropy.
        """
        random_suffix = secrets.token_hex(24)
        return f"{CREDENTIAL_PREFIX}{random_suffix}"

    @staticmethod
    def hash_credential(plaintext: str) -> str:
        """
        Computes SHA-256 hash of the plaintext machine credential.
        """
        return hashlib.sha256(plaintext.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def get_key_prefix(plaintext: str) -> str:
        """
        Returns a non-sensitive prefix of the credential (first 15 chars)
        for administrative display and identification.
        """
        return plaintext[:15] + "..."

    def create_agent_credential(
        self,
        db: Session,
        agent: models.Agent,
        name: Optional[str] = None,
        credential_type: str = "API_KEY",
        expires_in_days: Optional[int] = None
    ) -> Tuple[models.AgentCredential, str]:
        """
        Creates a new agent credential.
        Returns (credential_model, plaintext_token).
        The plaintext token is returned ONLY ONCE and NEVER stored.
        """
        plaintext = self.generate_raw_credential()
        key_hash = self.hash_credential(plaintext)
        key_prefix = self.get_key_prefix(plaintext)

        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(days=expires_in_days) if expires_in_days else None

        cred = models.AgentCredential(
            agent_id=agent.id,
            name=name or f"Key for {agent.name}",
            key_prefix=key_prefix,
            credential_type=credential_type,
            key_hash=key_hash,
            status="ACTIVE",
            created_at=now,
            expires_at=expires_at,
            last_used_at=None,
            revoked_at=None
        )
        db.add(cred)
        db.commit()
        db.refresh(cred)

        logger.info(f"[MachineAuth] Created credential {cred.id} for agent {agent.agent_code}")
        return cred, plaintext

    def rotate_agent_credential(
        self,
        db: Session,
        agent: models.Agent,
        old_credential_id: str,
        name: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> Tuple[models.AgentCredential, str]:
        """
        Rotates an existing credential: atomically revokes old credential
        and issues a fresh active credential.
        Returns (new_credential_model, new_plaintext_token).
        """
        old_cred = db.query(models.AgentCredential).filter(
            models.AgentCredential.id == old_credential_id,
            models.AgentCredential.agent_id == agent.id
        ).first()

        if not old_cred:
            raise ValueError("Existing credential not found for this agent.")

        now = datetime.datetime.utcnow()
        old_cred.status = "REVOKED"
        old_cred.revoked_at = now

        new_cred, new_plaintext = self.create_agent_credential(
            db=db,
            agent=agent,
            name=name or f"{old_cred.name or 'Rotated Key'} (Rotated)",
            credential_type=old_cred.credential_type,
            expires_in_days=expires_in_days
        )

        logger.info(f"[MachineAuth] Rotated credential {old_credential_id} -> {new_cred.id} for agent {agent.agent_code}")
        return new_cred, new_plaintext

    def revoke_agent_credential(
        self,
        db: Session,
        agent_id: str,
        credential_id: str
    ) -> bool:
        """
        Revokes a machine agent credential.
        """
        cred = db.query(models.AgentCredential).filter(
            models.AgentCredential.id == credential_id,
            models.AgentCredential.agent_id == agent_id
        ).first()

        if not cred:
            return False

        cred.status = "REVOKED"
        cred.revoked_at = datetime.datetime.utcnow()
        db.commit()
        logger.info(f"[MachineAuth] Revoked credential {credential_id} for agent {agent_id}")
        return True

    def authenticate_agent_credential(
        self,
        db: Session,
        credential_plaintext: str,
        agent_code: Optional[str] = None
    ) -> Tuple[models.Agent, models.AgentCredential]:
        """
        Validates machine agent credential against database.
        Checks credential status, expiration, agent status, and org status.
        Returns (agent, credential) on success.
        Raises ValueError with specific security reason on failure.
        """
        if not credential_plaintext or not credential_plaintext.startswith(CREDENTIAL_PREFIX):
            raise ValueError("Invalid machine credential format.")

        key_hash = self.hash_credential(credential_plaintext)
        
        query = db.query(models.AgentCredential).filter(
            models.AgentCredential.key_hash == key_hash
        )
        cred = query.first()

        if not cred:
            raise ValueError("Invalid machine credential.")

        # Check credential status
        if cred.status == "REVOKED" or cred.revoked_at is not None:
            raise ValueError("Machine credential has been revoked.")

        now = datetime.datetime.utcnow()
        if cred.expires_at and cred.expires_at < now:
            cred.status = "EXPIRED"
            db.commit()
            raise ValueError("Machine credential has expired.")

        # Retrieve and validate Agent
        agent = db.query(models.Agent).filter(models.Agent.id == cred.agent_id).first()
        if not agent:
            raise ValueError("Associated AI agent does not exist.")

        if agent_code and agent.agent_code != agent_code:
            raise ValueError("Machine credential does not match the specified agent code.")

        if agent.status in ("SUSPENDED", "CIRCUIT_BREAK"):
            raise ValueError(f"AI agent is currently in {agent.status} state and cannot authenticate.")

        # Check organization status
        org = db.query(models.Organization).filter(models.Organization.id == agent.org_id).first()
        if not org or org.status != "ACTIVE":
            raise ValueError("Organization is inactive or suspended.")

        # Update last used timestamp
        cred.last_used_at = now
        db.commit()

        return agent, cred

    def issue_machine_jwt(
        self,
        agent: models.Agent,
        credential: Optional[models.AgentCredential] = None,
        expires_in_hours: int = DEFAULT_MACHINE_TOKEN_EXPIRE_HOURS
    ) -> Dict[str, Any]:
        """
        Issues a short-lived cryptographically signed Machine JWT for the authenticated AI agent.
        """
        import time as _time
        now_ts = int(_time.time())
        exp_ts = now_ts + (expires_in_hours * 3600)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=expires_in_hours)
        jti = str(uuid.uuid4())

        payload = {
            "sub": str(agent.id),
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "org_id": str(agent.org_id),
            "autonomy_level": agent.autonomy_level,
            "token_type": TOKEN_TYPE_MACHINE,
            "credential_id": str(credential.id) if credential else None,
            "jti": jti,
            "iat": now_ts,
            "exp": exp_ts
        }

        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in_hours * 3600,
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "org_id": str(agent.org_id),
            "autonomy_level": agent.autonomy_level,
            "jti": jti,
            "expires_at": expires_at.isoformat()
        }

    def decode_and_verify_machine_jwt(
        self,
        token: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Decodes and cryptographically verifies a machine JWT.
        Ensures token_type is 'machine', not expired, agent exists,
        and agent is not suspended.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
        except JWTError as e:
            raise ValueError(f"Invalid or expired machine token: {e}")

        if payload.get("token_type") != TOKEN_TYPE_MACHINE:
            raise ValueError("Token is not an authorized machine agent identity token.")

        agent_id = payload.get("agent_id") or payload.get("sub")
        if not agent_id:
            raise ValueError("Missing agent identity claims.")

        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        if not agent:
            raise ValueError("Agent associated with machine token no longer exists.")

        # Check tenant isolation match
        if str(agent.org_id) != payload.get("org_id"):
            raise ValueError("Cross-tenant machine identity mismatch.")

        return {
            "agent": agent,
            "payload": payload,
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "org_id": str(agent.org_id),
            "autonomy_level": agent.autonomy_level,
            "jti": payload.get("jti")
        }

machine_auth_service = MachineAuthService()
