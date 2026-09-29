from database import engine
from sqlalchemy import text
import requests
import time
from config import settings

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = "Blackbird@12."

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

def clean_and_signup():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    print("=" * 75)
    print("  CLEANING INCOMPLETE AUTH USERS AND SIGNING UP VIA GOTRUE  ")
    print("=" * 75)

    with engine.connect() as conn:
        org_row = conn.execute(text("SELECT id FROM public.organizations LIMIT 1;")).first()
        org_id = str(org_row.id) if org_row else None

        for acc in ACCOUNTS:
            email = acc["email"]
            role = acc["role"]
            full_name = acc["full_name"]
            dept = acc["dept"]

            # Check if login works
            login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
            resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)

            if resp.status_code != 200:
                # Delete corrupted auth user & identity rows
                conn.execute(text("DELETE FROM auth.identities WHERE user_id IN (SELECT id FROM auth.users WHERE email = :email);"), {"email": email})
                conn.execute(text("DELETE FROM auth.users WHERE email = :email;"), {"email": email})
                conn.commit()
                print(f"  [CLEANUP] Deleted broken auth records for: {email}")

                # Call official Supabase Auth SignUp API
                signup_url = f"{SUPABASE_URL}/auth/v1/signup"
                signup_resp = requests.post(signup_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)
                print(f"  [SIGNUP] GoTrue signup for {email}: {signup_resp.status_code}")

                # Confirm email in PostgreSQL
                time.sleep(1.0)
                conn.execute(text("UPDATE auth.users SET email_confirmed_at = NOW() WHERE email = :email;"), {"email": email})
                conn.commit()

            # Link auth_user_id in public.users
            auth_row = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()
            if auth_row:
                auth_id_str = str(auth_row.id)
                user_exists = conn.execute(text("SELECT id FROM public.users WHERE email = :email;"), {"email": email}).first()
                if not user_exists:
                    conn.execute(
                        text("""
                            INSERT INTO public.users (id, org_id, auth_user_id, email, full_name, role, department, status, created_at, updated_at)
                            VALUES (gen_random_uuid(), :org_id, :auth_id, :email, :name, :role, :dept, 'ACTIVE', NOW(), NOW());
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

            time.sleep(1.5)

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
    clean_and_signup()
