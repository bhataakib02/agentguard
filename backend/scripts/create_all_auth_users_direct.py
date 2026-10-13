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
        "[AgentGuard Security Block] create_all_auth_users_direct script cannot be executed in PRODUCTION."
    )

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = os.getenv("DEMO_ACCOUNTS_PASSWORD", secrets.token_urlsafe(16))
BCRYPT_HASH = passlib.hash.bcrypt.hash(TEST_PASSWORD)

ACCOUNTS = [
    {"email": "user@agentguard.com", "role": "USER", "full_name": "User Account", "dept": "General"},
    {"email": "viewer@agentguard.com", "role": "VIEWER", "full_name": "Viewer Account", "dept": "Analytics"},
    {"email": "analyst@agentguard.com", "role": "ANALYST", "full_name": "Analyst Account", "dept": "AI Governance"},
    {"email": "operator@agentguard.com", "role": "OPERATOR", "full_name": "Operator Account", "dept": "Runtime Operations"},
    {"email": "security.analyst@agentguard.com", "role": "SECURITY_ANALYST", "full_name": "Security Analyst Account", "dept": "SOC Response"},
    {"email": "manager@agentguard.com", "role": "MANAGER", "full_name": "Manager Account", "dept": "Management"},
    {"email": "developer@agentguard.com", "role": "DEVELOPER", "full_name": "Developer Account", "dept": "Engineering"},
    {"email": "admin@agentguard.com", "role": "ADMIN", "full_name": "Admin Account", "dept": "Administration"},
    {"email": "superadmin@agentguard.com", "role": "SUPER_ADMIN", "full_name": "Super Admin Account", "dept": "Leadership"}
]

def seed_real_supabase_accounts():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    print("=" * 75)
    print("  SEEDING TEST SUPABASE AUTH USERS & IDENTITIES IN NON-PRODUCTION  ")
    print("=" * 75)

    with engine.connect() as conn:
        org_row = conn.execute(text("SELECT id FROM public.organizations LIMIT 1;")).first()
        org_id = str(org_row.id) if org_row else None

        for acc in ACCOUNTS:
            email = acc["email"]
            role = acc["role"]
            name = acc["full_name"]
            dept = acc["dept"]

            auth_user = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()
            if not auth_user:
                auth_res = conn.execute(
                    text("""
                        INSERT INTO auth.users (
                            id, instance_id, email, encrypted_password, email_confirmed_at,
                            raw_app_meta_data, raw_user_meta_data, is_super_admin, role, aud
                        ) VALUES (
                            gen_random_uuid(), '00000000-0000-0000-0000-000000000000',
                            :email, :pwd, NOW(),
                            :app_meta, :user_meta, :is_super, 'authenticated', 'authenticated'
                        ) RETURNING id;
                    """),
                    {
                        "email": email,
                        "pwd": BCRYPT_HASH,
                        "app_meta": json.dumps({"provider": "email", "providers": ["email"], "role": role}),
                        "user_meta": json.dumps({"full_name": name, "department": dept, "role": role}),
                        "is_super": True if role == "SUPER_ADMIN" else False
                    }
                )
                auth_id = str(auth_res.first().id)
            else:
                auth_id = str(auth_user.id)

            user_exists = conn.execute(text("SELECT id FROM public.users WHERE email = :email;"), {"email": email}).first()
            if not user_exists:
                conn.execute(
                    text("""
                        INSERT INTO public.users (
                            id, org_id, auth_user_id, email, full_name, role, department, status
                        ) VALUES (
                            gen_random_uuid(), :org_id, :auth_id, :email, :name, :role, :dept, 'ACTIVE'
                        );
                    """),
                    {"org_id": org_id if role != "SUPER_ADMIN" else None, "auth_id": auth_id, "email": email, "name": name, "role": role, "dept": dept}
                )
            conn.commit()

if __name__ == "__main__":
    seed_real_supabase_accounts()
