from database import engine
from sqlalchemy import text
import requests
import passlib.hash
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

def force_set_all_passwords():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    print("=" * 75)
    print("  FORCING BCRYPT PASSWORD HASH & CONFIRMATION FOR ALL 9 SUPABASE ACCOUNTS  ")
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

    print("\n  VERIFYING LOGIN FOR ALL 9 ACCOUNTS VIA SUPABASE AUTH API...")
    results = []

    for acc in ACCOUNTS:
        email = acc["email"]
        role = acc["role"]

        login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)

        if resp.status_code == 200:
            results.append((role, email, "100% VERIFIED LOGIN SUCCESS"))
        else:
            results.append((role, email, f"FAILED ({resp.status_code}): {resp.text}"))

    print("\n" + "=" * 75)
    print("      FINAL REAL SUPABASE AUTH ACCOUNTS STATUS MATRIX      ")
    print("=" * 75)
    for r in results:
        print(f"  • {r[0]:<18} | {r[1]:<32} | {r[2]}")
    print("=" * 75)

if __name__ == "__main__":
    force_set_all_passwords()
