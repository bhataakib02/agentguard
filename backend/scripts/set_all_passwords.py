import os
import secrets
from database import engine
from sqlalchemy import text
import requests
import passlib.hash
from config import settings

if settings.ENVIRONMENT == "production":
    raise RuntimeError(
        "[AgentGuard Security Block] set_all_passwords script cannot be executed in PRODUCTION."
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

def force_set_all_passwords():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    print("=" * 75)
    print("  FORCING BCRYPT PASSWORD HASH & CONFIRMATION FOR NON-PRODUCTION TEST ACCOUNTS  ")
    print("=" * 75)

    with engine.connect() as conn:
        for acc in ACCOUNTS:
            email = acc["email"]
            role = acc["role"]

            # Update auth.users encrypted password and confirmation
            conn.execute(
                text("UPDATE auth.users SET encrypted_password = :hash, email_confirmed_at = NOW() WHERE email = :email;"),
                {"hash": BCRYPT_HASH, "email": email}
            )
            conn.commit()

            # Ensure public.users record exists and links role
            auth_row = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()
            if auth_row:
                org_row = conn.execute(text("SELECT id FROM public.organizations LIMIT 1;")).first()
                org_id = str(org_row.id) if org_row else None

                user_exists = conn.execute(text("SELECT id FROM public.users WHERE email = :email;"), {"email": email}).first()
                if not user_exists:
                    conn.execute(
                        text("INSERT INTO public.users (id, org_id, auth_user_id, email, full_name, role, status) VALUES (gen_random_uuid(), :org_id, :auth_id, :email, :name, :role, 'ACTIVE');"),
                        {"org_id": org_id, "auth_id": str(auth_row.id), "email": email, "name": f"{role.replace('_', ' ').title()} Account", "role": role}
                    )
                else:
                    conn.execute(
                        text("UPDATE public.users SET auth_user_id = :auth_id, role = :role, status = 'ACTIVE' WHERE email = :email;"),
                        {"auth_id": str(auth_row.id), "role": role, "email": email}
                    )
                conn.commit()

if __name__ == "__main__":
    force_set_all_passwords()
