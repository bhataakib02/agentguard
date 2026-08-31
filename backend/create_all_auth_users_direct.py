from database import engine
from sqlalchemy import text
import requests
import passlib.hash
import json
from config import settings

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = "Blackbird@12."
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
    {"email": "thefreelancer2076@gmail.com", "role": "SUPER_ADMIN", "full_name": "Super Admin Account", "dept": "Leadership"}
]

def seed_real_supabase_accounts():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    print("=" * 75)
    print("  SEEDING REAL SUPABASE AUTH USERS & IDENTITIES DIRECTLY  ")
    print("=" * 75)

    with engine.connect() as conn:
        org_row = conn.execute(text("SELECT id FROM public.organizations LIMIT 1;")).first()
        org_id = str(org_row.id) if org_row else None

        for acc in ACCOUNTS:
            email = acc["email"]
            role = acc["role"]
            full_name = acc["full_name"]
            dept = acc["dept"]

            # 1. Upsert into auth.users
            existing_auth = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()
            if not existing_auth:
                conn.execute(
                    text("""
                        INSERT INTO auth.users (
                            id, instance_id, aud, role, email, encrypted_password, email_confirmed_at,
                            raw_app_meta_data, raw_user_meta_data, created_at, updated_at, is_super_admin
                        ) VALUES (
                            gen_random_uuid(), '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
                            :email, :hash, NOW(), '{"provider":"email","providers":["email"]}', '{}', NOW(), NOW(), false
                        );
                    """),
                    {"email": email, "hash": BCRYPT_HASH}
                )
                conn.commit()
                existing_auth = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()

            auth_id_str = str(existing_auth.id)

            conn.execute(
                text("UPDATE auth.users SET encrypted_password = :hash, email_confirmed_at = NOW() WHERE email = :email;"),
                {"email": email, "hash": BCRYPT_HASH}
            )
            conn.commit()

            # 2. Upsert into auth.identities
            existing_identity = conn.execute(text("SELECT id FROM auth.identities WHERE user_id = :u_id;"), {"u_id": auth_id_str}).first()
            identity_data_json = json.dumps({"sub": auth_id_str, "email": email, "email_verified": True})

            if not existing_identity:
                conn.execute(
                    text("""
                        INSERT INTO auth.identities (
                            id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
                        ) VALUES (
                            gen_random_uuid(), :u_id, CAST(:id_data AS jsonb), 'email', :email, NOW(), NOW(), NOW()
                        );
                    """),
                    {"u_id": auth_id_str, "id_data": identity_data_json, "email": email}
                )
                conn.commit()
            else:
                conn.execute(
                    text("""
                        UPDATE auth.identities 
                        SET identity_data = CAST(:id_data AS jsonb), updated_at = NOW() 
                        WHERE user_id = :u_id;
                    """),
                    {"u_id": auth_id_str, "id_data": identity_data_json}
                )
                conn.commit()

            # 3. Upsert into public.users
            existing_user = conn.execute(text("SELECT id FROM public.users WHERE email = :email;"), {"email": email}).first()
            if not existing_user:
                conn.execute(
                    text("""
                        INSERT INTO public.users (
                            id, org_id, auth_user_id, email, full_name, role, department, status, created_at, updated_at
                        ) VALUES (
                            gen_random_uuid(), :org_id, :auth_id, :email, :name, :role, :dept, 'ACTIVE', NOW(), NOW()
                        );
                    """),
                    {"org_id": org_id, "auth_id": auth_id_str, "email": email, "name": full_name, "role": role, "dept": dept}
                )
            else:
                conn.execute(
                    text("""
                        UPDATE public.users 
                        SET auth_user_id = :auth_id, role = :role, department = :dept, status = 'ACTIVE', updated_at = NOW() 
                        WHERE email = :email;
                    """),
                    {"auth_id": auth_id_str, "role": role, "dept": dept, "email": email}
                )
            conn.commit()
            print(f"  [SUPABASE AUTH & PUBLIC DB] Provisioned: {email:<32} -> Role: {role}")

    print("\n" + "=" * 75)
    print("  VERIFYING REAL SUPABASE AUTH LOGINS FOR ALL 9 ACCOUNTS  ")
    print("=" * 75)

    results = []
    for acc in ACCOUNTS:
        email = acc["email"]
        role = acc["role"]

        login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)

        if resp.status_code == 200:
            results.append((role, email, "100% VERIFIED PASS (200 OK)"))
        else:
            results.append((role, email, f"FAILED ({resp.status_code}): {resp.text}"))

    print("\n" + "=" * 75)
    print("      FINAL REAL SUPABASE AUTH ACCOUNTS VERIFICATION MATRIX      ")
    print("=" * 75)
    for r in results:
        print(f"  • {r[0]:<18} | {r[1]:<32} | {r[2]}")
    print("=" * 75)

if __name__ == "__main__":
    seed_real_supabase_accounts()
