import datetime
from datetime import timedelta
from typing import Optional, List
from jose import jwt
from passlib.context import CryptContext
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
    email: Optional[str] = None,
    role: Optional[str] = None,
    additional_claims: Optional[dict] = None
) -> str:
    if expires_delta:
        expire = utcnow() + expires_delta
    else:
        expire = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(user_id), "exp": expire}
    if email:
        to_encode["email"] = email
    if role:
        to_encode["role"] = role
    if additional_claims:
        to_encode.update(additional_claims)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


import base64
import os
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

_sec_logger = logging.getLogger("agentguard.security")

def _get_encryption_keys() -> List[bytes]:
    """
    Returns candidate AES-256-GCM encryption keys.
    Key 0 is the primary active key for new encryptions.
    Subsequent keys are historical rotation keys (e.g. LOCAL_AES_MASTER_KEY_PREVIOUS)
    used to ensure existing ciphertext remains decryptable during migration windows.
    """
    keys = []
    
    # 1. Primary dedicated AES master key
    master_env = os.getenv("LOCAL_AES_MASTER_KEY")
    if master_env:
        try:
            if len(master_env) == 64:
                keys.append(bytes.fromhex(master_env))
            else:
                keys.append(base64.b64decode(master_env)[:32])
        except Exception as e:
            _sec_logger.error(f"Failed to parse LOCAL_AES_MASTER_KEY: {e}")

    # 2. Previous rotation key (during key transition window)
    prev_env = os.getenv("LOCAL_AES_MASTER_KEY_PREVIOUS")
    if prev_env:
        try:
            if len(prev_env) == 64:
                keys.append(bytes.fromhex(prev_env))
            else:
                keys.append(base64.b64decode(prev_env)[:32])
        except Exception as e:
            _sec_logger.error(f"Failed to parse LOCAL_AES_MASTER_KEY_PREVIOUS: {e}")

    # 3. Deterministic key derived from settings.SECRET_KEY via HKDF-SHA256
    raw_secret = getattr(settings, "SECRET_KEY", "agentguard-default-key-for-dev").encode("utf-8")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"agentguard-encryption-salt-v1",
        info=b"agentguard-at-rest-encryption-key"
    )
    keys.append(hkdf.derive(raw_secret))
    return keys

def encrypt_secret_at_rest(plaintext: str) -> str:
    """
    Encrypts a sensitive secret string using AES-256-GCM using the active primary key.
    Returns: 'enc:aesgcm:<nonce_b64>:<ciphertext_b64>'
    """
    if not plaintext:
        return ""
    keys = _get_encryption_keys()
    active_key = keys[0]
    aesgcm = AESGCM(active_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    nonce_b64 = base64.b64encode(nonce).decode("utf-8")
    ct_b64 = base64.b64encode(ciphertext).decode("utf-8")
    return f"enc:aesgcm:{nonce_b64}:{ct_b64}"

def decrypt_secret_at_rest(encrypted_val: Optional[str]) -> Optional[str]:
    """
    Decrypts an AES-256-GCM encrypted secret.
    Attempts primary active key, then historical rotation keys in order.
    Gracefully handles unencrypted legacy values for backward compatibility.
    Fails closed and returns None if ciphertext is corrupt, tampered, or untrusted.
    """
    if not encrypted_val:
        return None
    if not encrypted_val.startswith("enc:aesgcm:"):
        # Legacy unencrypted value (backward compatibility)
        return encrypted_val
    try:
        parts = encrypted_val.split(":", 3)
        if len(parts) != 4:
            return None
        nonce_b64, ct_b64 = parts[2], parts[3]
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ct_b64)

        candidate_keys = _get_encryption_keys()
        for key in candidate_keys:
            try:
                aesgcm = AESGCM(key)
                plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
                return plaintext_bytes.decode("utf-8")
            except Exception:
                continue
        _sec_logger.warning("Failed to decrypt secret at rest: all candidate keys failed authentication tag check.")
        return None
    except Exception as e:
        _sec_logger.warning(f"Failed to decrypt secret at rest: {e}")
        return None
