import os
import secrets
from database import engine
from sqlalchemy import text
import requests
import passlib.hash
import json
from config import settings

if settings.ENVIRONMENT == "production":
    raise RuntimeError(
        "[AgentGuard Security Block] fix_identities script cannot be executed in PRODUCTION."
    )

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = os.getenv("DEMO_ACCOUNTS_PASSWORD", secrets.token_urlsafe(16))
BCRYPT_HASH = passlib.hash.bcrypt.hash(TEST_PASSWORD)

ACCOUNTS = [
    {"email": "user@agentguard.com", "role": "USER"},
    {"email": "viewer@agentguard.com", "role": "VIEWER"},
    {"email": "analyst@agentguard.com", "role": "ANALYST"},
    {"email": "operator@agentguard.com", "role": "OPERATOR"},
    {"email": "security.analyst@agentguard.com", "role": "SECURITY_ANALYST"},
    {"email": "manager@agentguard.com", "role": "MANAGER"},
    {"email": "developer@agentguard.com", "role": "DEVELOPER"},
    {"email": "admin@agentguard.com", "role": "ADMIN"},
    {"email": "superadmin@agentguard.com", "role": "SUPER_ADMIN"}
]

def fix_all_identities():
    with engine.connect() as conn:
        for acc in ACCOUNTS:
            email = acc["email"]
            auth_user = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()
            if auth_user:
                auth_id = str(auth_user.id)
                ident = conn.execute(text("SELECT id FROM auth.identities WHERE user_id = :uid;"), {"uid": auth_id}).first()
                if not ident:
                    conn.execute(
                        text("""
                            INSERT INTO auth.identities (
                                id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
                            ) VALUES (
                                :uid, :uid, :data, 'email', NOW(), NOW(), NOW()
                            );
                        """),
                        {"uid": auth_id, "data": json.dumps({"sub": auth_id, "email": email})}
                    )
                    conn.commit()

if __name__ == "__main__":
    fix_all_identities()
