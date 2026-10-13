"""
AGENTGUARD — Webhook Secret Encryption Migration Utility
Safely and idempotently migrates legacy plaintext webhook signing secrets to AES-256-GCM encryption at rest.

Safety Rules:
- Never prints or logs raw/plaintext secrets.
- Idempotent: endpoints already starting with 'enc:aesgcm:' are left untouched.
- Reversible / Dry-Run capable.
- Never runs against production without explicit safety confirmation flag.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import SessionLocal
import models
from core.security import encrypt_secret_at_rest, decrypt_secret_at_rest
from config import settings

logger = logging.getLogger("agentguard.migrations.webhooks")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def migrate_webhook_secrets(dry_run: bool = True, db_session = None) -> dict:
    """
    Encrypts any unencrypted webhook endpoint secret keys.
    Returns audit statistics without logging secret values.
    """
    if not dry_run and settings.ENVIRONMENT == "production":
        confirm = os.getenv("CONFIRM_PRODUCTION_WEBHOOK_MIGRATION", "")
        if confirm != "CONFIRMED":
            raise RuntimeError(
                "[AgentGuard Safety Block] Production migration requires explicit environment variable "
                "CONFIRM_PRODUCTION_WEBHOOK_MIGRATION=CONFIRMED."
            )

    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        endpoints = db.query(models.WebhookEndpoint).all()
        total_endpoints = len(endpoints)
        already_encrypted = 0
        migrated = 0
        skipped_no_secret = 0

        for ep in endpoints:
            if not ep.secret_key:
                skipped_no_secret += 1
                continue

            if ep.secret_key.startswith("enc:aesgcm:"):
                already_encrypted += 1
                continue

            # Legacy plaintext secret found
            if not dry_run:
                encrypted = encrypt_secret_at_rest(ep.secret_key)
                ep.secret_key = encrypted
                migrated += 1
            else:
                migrated += 1

        if not dry_run and migrated > 0:
            db.commit()
            logger.info(f"[Migration] Successfully committed {migrated} encrypted webhook secret(s).")
        elif dry_run:
            logger.info(f"[Dry Run] Found {migrated} webhook secret(s) requiring encryption. (No changes committed)")

        summary = {
            "total_endpoints": total_endpoints,
            "already_encrypted": already_encrypted,
            "migrated": migrated,
            "skipped_no_secret": skipped_no_secret,
            "dry_run": dry_run
        }
        return summary
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    is_dry = "--commit" not in sys.argv
    result = migrate_webhook_secrets(dry_run=is_dry)
    print("Migration result:", result)
