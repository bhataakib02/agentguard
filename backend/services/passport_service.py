import os
import base64
import json
import logging
import datetime
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from config import settings

logger = logging.getLogger("agentguard.passport")

class PassportSigningService:
    """
    Asymmetric Cryptographic Passport Signing & Verification Engine.
    Uses Ed25519 asymmetric cryptography to sign and verify canonical
    Agent Passports, guaranteeing non-repudiation, tamper-evidence,
    and zero-trust machine agent provenance.
    """

    def __init__(self):
        self._private_key: Optional[ed25519.Ed25519PrivateKey] = None
        self._public_key: Optional[ed25519.Ed25519PublicKey] = None
        self._key_id = os.getenv("AGENTGUARD_PASSPORT_KEY_ID", "agentguard-root-ed25519-v1")
        self._trusted_keys: Dict[str, ed25519.Ed25519PublicKey] = {}
        self._initialize_keys()

    def _initialize_keys(self):
        """
        Loads the Ed25519 private key from environment or deterministically
        derives it from SECRET_KEY using HKDF-SHA256 to ensure safe, repeatable
        key lifecycle without hardcoding secrets in source code.
        """
        env_key = os.getenv("AGENTGUARD_PASSPORT_PRIVATE_KEY")
        if env_key:
            try:
                # Support base64 or hex raw 32-byte seed
                if len(env_key) == 64:
                    raw_bytes = bytes.fromhex(env_key)
                else:
                    raw_bytes = base64.b64decode(env_key)
                self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes[:32])
                logger.info("[PassportService] Initialized from AGENTGUARD_PASSPORT_PRIVATE_KEY")
            except Exception as e:
                logger.error(f"[PassportService] Failed to load key from env: {e}")

        if not self._private_key:
            # Deterministically derive 32-byte seed from SECRET_KEY
            secret = getattr(settings, "SECRET_KEY", "agentguard-default-signing-key").encode("utf-8")
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"agentguard-passport-salt-v1",
                info=b"agentguard-passport-ed25519-seed"
            )
            derived_seed = hkdf.derive(secret)
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(derived_seed)
            logger.info("[PassportService] Initialized deterministic platform Ed25519 root key")

        self._public_key = self._private_key.public_key()
        self._trusted_keys[self._key_id] = self._public_key

    def register_rotation_public_key(self, key_id: str, public_key_bytes: bytes):
        """Registers a historical or rotated public key into the verification keyring."""
        pub = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        self._trusted_keys[key_id] = pub

    @property
    def key_id(self) -> str:
        return self._key_id

    def get_public_key_bytes(self) -> bytes:
        return self._public_key.public_bytes_raw()

    def get_public_key_b64(self) -> str:
        return base64.b64encode(self.get_public_key_bytes()).decode("utf-8")

    def get_public_key_hex(self) -> str:
        return self.get_public_key_bytes().hex()

    def canonicalize_passport_data(
        self,
        agent: Any,
        passport: Any,
        capabilities: Optional[List[str]] = None
    ) -> bytes:
        """
        Creates a deterministic, sorted, whitespace-free canonical JSON representation
        of the passport and agent identity for digital signature hashing.
        """
        if capabilities is None and hasattr(passport, "claims") and isinstance(passport.claims, dict):
            capabilities = passport.claims.get("capabilities", [])
        elif capabilities is None and hasattr(passport, "capabilities") and isinstance(passport.capabilities, list):
            capabilities = passport.capabilities

        issued_at_str = passport.issued_at.isoformat() if hasattr(passport.issued_at, "isoformat") else str(passport.issued_at)
        expires_at_str = passport.expires_at.isoformat() if hasattr(passport.expires_at, "isoformat") else str(passport.expires_at)

        payload: Dict[str, Any] = {
            "agent_code": getattr(agent, "agent_code", ""),
            "agent_id": str(getattr(agent, "id", "")),
            "autonomy_level": getattr(agent, "autonomy_level", "MEDIUM"),
            "capabilities": sorted(capabilities or []),
            "department": getattr(agent, "department", ""),
            "environment": getattr(agent, "environment", "PRODUCTION"),
            "expires_at": expires_at_str,
            "issued_at": issued_at_str,
            "key_id": getattr(passport, "key_id", self._key_id) or self._key_id,
            "model_name": getattr(agent, "model_name", ""),
            "model_version": getattr(agent, "model_version", ""),
            "org_id": str(getattr(agent, "org_id", "")),
            "owner_id": str(getattr(agent, "owner_id", "") or ""),
            "passport_number": getattr(passport, "passport_number", ""),
            "passport_version": getattr(passport, "passport_version", "1.0") or "1.0",
            "purpose": getattr(agent, "purpose", ""),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sign_passport(
        self,
        agent: Any,
        passport: Any,
        capabilities: Optional[List[str]] = None
    ) -> str:
        """
        Signs the canonical passport payload with the platform Ed25519 private key.
        Returns the formatted signature: 'ed25519:<base64-signature>'.
        """
        canonical_bytes = self.canonicalize_passport_data(agent, passport, capabilities)
        signature = self._private_key.sign(canonical_bytes)
        sig_str = f"ed25519:{base64.b64encode(signature).decode('utf-8')}"
        
        # Store metadata on passport object
        passport.digital_signature = sig_str
        passport.algorithm = "Ed25519"
        passport.key_id = self._key_id
        passport.passport_version = "1.0"
        try:
            passport.claims = json.loads(canonical_bytes.decode("utf-8"))
        except Exception:
            passport.claims = None

        return sig_str

    def rotate_active_key(self, new_key_id: str, new_private_key: ed25519.Ed25519PrivateKey):
        """
        Rotates the active platform signing key.
        The previous active key remains in _trusted_keys to verify historical passports.
        """
        if not new_key_id:
            raise ValueError("New key_id cannot be empty.")
        self._key_id = new_key_id
        self._private_key = new_private_key
        self._public_key = new_private_key.public_key()
        self._trusted_keys[new_key_id] = self._public_key
        logger.info(f"[PassportService] Rotated active signing key to '{new_key_id}'")

    def verify_passport(
        self,
        passport: Any,
        agent: Optional[Any] = None,
        capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Cryptographically verifies the digital signature, validity period,
        and revocation status of an Agent Passport.
        Strictly selects trusted public keys using the passport's key_id.
        Rejects unknown or missing key IDs safely.
        """
        if not passport:
            return {
                "valid": False,
                "status": "MISSING",
                "reason": "Agent passport record not found."
            }

        # 1. Check revocation status
        if getattr(passport, "verification_status", None) == "REVOKED":
            return {
                "valid": False,
                "status": "REVOKED",
                "reason": "Agent passport has been explicitly revoked."
            }

        # 2. Check expiration
        now = datetime.datetime.utcnow()
        expires_at = getattr(passport, "expires_at", None)
        if expires_at and expires_at < now:
            passport.verification_status = "EXPIRED"
            return {
                "valid": False,
                "status": "EXPIRED",
                "reason": f"Agent passport expired on {expires_at.isoformat()}."
            }

        # 3. Check Agent lifecycle status if agent is supplied
        if agent:
            agent_status = getattr(agent, "status", "NORMAL")
            if agent_status in ("SUSPENDED", "CIRCUIT_BREAK"):
                return {
                    "valid": False,
                    "status": f"AGENT_{agent_status}",
                    "reason": f"Associated AI agent is currently {agent_status}."
                }

        # 4. Check Key ID: Must be present and registered in trusted keys keyring
        key_id = getattr(passport, "key_id", None)
        if not key_id:
            return {
                "valid": False,
                "status": "UNKNOWN_KEY_ID",
                "reason": "Passport is missing required key_id."
            }

        if key_id not in self._trusted_keys:
            return {
                "valid": False,
                "status": "UNKNOWN_KEY_ID",
                "reason": f"Untrusted or unrecognized passport key ID '{key_id}'."
            }

        trusted_pub = self._trusted_keys[key_id]

        # 5. Check digital signature
        sig_raw = getattr(passport, "digital_signature", "")
        if not sig_raw or not sig_raw.startswith("ed25519:"):
            # Legacy or unverified dummy hash
            return {
                "valid": False,
                "status": "UNVERIFIED",
                "reason": "Passport does not contain a valid Ed25519 cryptographic digital signature."
            }

        try:
            b64_sig = sig_raw.split("ed25519:", 1)[1]
            signature_bytes = base64.b64decode(b64_sig)
            
            # Reconstruct canonical bytes
            canonical_bytes = self.canonicalize_passport_data(agent, passport, capabilities)
            
            # Verify signature with the selected trusted public key
            trusted_pub.verify(signature_bytes, canonical_bytes)
            
            passport.verification_status = "VERIFIED"
            return {
                "valid": True,
                "status": "VERIFIED",
                "algorithm": "Ed25519",
                "key_id": key_id,
                "reason": f"Cryptographically verified with trusted Ed25519 public key '{key_id}'."
            }
        except Exception as e:
            logger.warning(f"[PassportService] Verification failed for passport {getattr(passport, 'passport_number', 'unknown')}: {e}")
            return {
                "valid": False,
                "status": "TAMPERED",
                "reason": f"Cryptographic signature mismatch: passport payload or agent identity has been tampered with ({e})."
            }

# Global singleton
passport_service = PassportSigningService()
