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
    {"email": "user@agentguard.com", "role": "USER"},
    {"email": "viewer@agentguard.com", "role": "VIEWER"},
    {"email": "analyst@agentguard.com", "role": "ANALYST"},
    {"email": "operator@agentguard.com", "role": "OPERATOR"},
    {"email": "security.analyst@agentguard.com", "role": "SECURITY_ANALYST"},
    {"email": "manager@agentguard.com", "role": "MANAGER"},
    {"email": "developer@agentguard.com", "role": "DEVELOPER"},
    {"email": "admin@agentguard.com", "role": "ADMIN"},
    {"email": "thefreelancer2076@gmail.com", "role": "SUPER_ADMIN"}
]

def fix_all_identities():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    with engine.connect() as conn:
        org_row = conn.execute(text("SELECT id FROM public.organizations LIMIT 1;")).first()
        org_id = str(org_row.id) if org_row else None

        for acc in ACCOUNTS:
            email = acc["email"]
            role = acc["role"]

            # 1. Ensure user exists in auth.users with correct password hash and email confirmation
            auth_user = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()
            if not auth_user:
                conn.execute(
                    text("""
                        INSERT INTO auth.users (
                            id, instance_id, aud, role, email, encrypted_password, email_confirmed_at,
                            raw_app_meta_data, raw_user_meta_data, created_at, updated_at, is_super_admin,
                            confirmation_token, recovery_token, email_change, email_change_token_new, phone_change
                        ) VALUES (
                            gen_random_uuid(), '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
                            :email, :hash, NOW(), '{"provider":"email","providers":["email"]}', '{}', NOW(), NOW(), false,
                            '', '', '', '', ''
                        );
                    """),
                    {"email": email, "hash": BCRYPT_HASH}
                )
                conn.commit()
                auth_user = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()

            user_id = str(auth_user.id)

            conn.execute(
                text("UPDATE auth.users SET encrypted_password = :hash, email_confirmed_at = NOW() WHERE email = :email;"),
                {"hash": BCRYPT_HASH, "email": email}
            )
            conn.commit()

            # 2. Fix auth.identities
            conn.execute(text("DELETE FROM auth.identities WHERE user_id = :u_id OR provider_id = :email;"), {"u_id": user_id, "email": email})
            conn.commit()

            id_data = json.dumps({"sub": user_id, "email": email, "email_verified": True})
            conn.execute(
                text("""
                    INSERT INTO auth.identities (
                        id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
                    ) VALUES (
                        :u_id, :u_id, CAST(:id_data AS jsonb), 'email', :user_id_str, NOW(), NOW(), NOW()
                    );
                """),
                {"u_id": user_id, "id_data": id_data, "user_id_str": user_id}
            )
            conn.commit()

            # 3. Fix public.users
            public_user = conn.execute(text("SELECT id FROM public.users WHERE email = :email;"), {"email": email}).first()
            if not public_user:
                conn.execute(
                    text("""
                        INSERT INTO public.users (id, org_id, auth_user_id, email, full_name, role, status, created_at, updated_at)
                        VALUES (gen_random_uuid(), :org_id, :auth_id, :email, :name, :role, 'ACTIVE', NOW(), NOW());
                    """),
                    {"org_id": org_id, "auth_id": user_id, "email": email, "name": f"{role.replace('_', ' ').title()} Account", "role": role}
                )
            else:
                conn.execute(
                    text("UPDATE public.users SET auth_user_id = :auth_id, role = :role, status = 'ACTIVE' WHERE email = :email;"),
                    {"auth_id": user_id, "role": role, "email": email}
                )
            conn.commit()

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
    fix_all_identities()
