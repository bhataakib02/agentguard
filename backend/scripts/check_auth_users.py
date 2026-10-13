import os
from database import engine, SessionLocal
from sqlalchemy import text
import requests
import time
from config import settings
import models

if settings.ENVIRONMENT == "production":
    raise RuntimeError(
        "[AgentGuard Security Block] check_auth_users script cannot be executed in PRODUCTION."
    )

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = os.getenv("DEMO_ACCOUNTS_PASSWORD", "")

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

def check_and_fix_auth_users():
    if not TEST_PASSWORD:
        print("DEMO_ACCOUNTS_PASSWORD not set. Skipping password verification check.")
        return
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    db = SessionLocal()
    try:
        for acc in ACCOUNTS:
            email = acc["email"]
            login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
            resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)
            print(f"Check {email}: {resp.status_code}")
    finally:
        db.close()

if __name__ == "__main__":
    check_and_fix_auth_users()
