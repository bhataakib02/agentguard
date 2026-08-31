from database import engine, SessionLocal
from sqlalchemy import text
import requests
import time
from config import settings
import models

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = "Blackbird@12."

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

def check_and_fix_auth_users():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    db = SessionLocal()

    with engine.connect() as conn:
        conn.execute(text("UPDATE auth.users SET email_confirmed_at = NOW() WHERE email_confirmed_at IS NULL;"))
        conn.commit()
        print("  [SUCCESS] Confirmed all user emails in Supabase auth.users!")

    print("\n" + "=" * 75)
    print("  VERIFYING AND FIXING SUPABASE AUTH PASSWORDS FOR ALL 9 ACCOUNTS  ")
    print("=" * 75)

    for item in ACCOUNTS:
        email = item["email"]
        role = item["role"]

        # 1. Attempt login
        login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)

        if resp.status_code == 200:
            print(f"  • {role:<18} | {email:<32} | PASS (200 OK)")
        else:
            print(f"  • {role:<18} | {email:<32} | FAILED ({resp.status_code}) -> Provisioning account...")
            signup_url = f"{SUPABASE_URL}/auth/v1/signup"
            signup_resp = requests.post(signup_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)
            
            time.sleep(1.0)
            with engine.connect() as conn:
                conn.execute(text("UPDATE auth.users SET email_confirmed_at = NOW() WHERE email = :email;"), {"email": email})
                conn.commit()

            # Retry login
            retry_resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)
            if retry_resp.status_code == 200:
                print(f"  • {role:<18} | {email:<32} | PASS AFTER FIX (200 OK)")
            else:
                print(f"  • {role:<18} | {email:<32} | RETRY LOG ({retry_resp.status_code}): {retry_resp.text}")

        # Update auth_user_id link in PostgreSQL users table
        with engine.connect() as conn:
            auth_row = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()
            if auth_row:
                conn.execute(text("UPDATE public.users SET auth_user_id = :auth_id, role = :role WHERE email = :email;"), {
                    "auth_id": str(auth_row.id),
                    "role": role,
                    "email": email
                })
                conn.commit()

    db.close()

if __name__ == "__main__":
    check_and_fix_auth_users()
