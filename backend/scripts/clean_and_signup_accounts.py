import os
import secrets
from database import engine
from sqlalchemy import text
import requests
import time
from config import settings

APPROVED_NON_PROD_DATABASES = {
    "agentguard_dev", "agentguard_test", "agentguard_local", "agentguard_ci", "test_agentguard"
}

if settings.ENVIRONMENT not in ("development", "test", "local", "ci"):
    raise RuntimeError(
        f"[AgentGuard Security Block] clean_and_signup_accounts script cannot be executed outside development/test (current environment: '{settings.ENVIRONMENT}')."
    )

from urllib.parse import urlparse
parsed = urlparse(settings.DATABASE_URL)
target_db = parsed.path.lstrip("/").split("?")[0]
if target_db not in APPROVED_NON_PROD_DATABASES:
    raise RuntimeError(
        f"[AgentGuard Security Block] Target database '{target_db}' is not in the approved non-production allowlist: {APPROVED_NON_PROD_DATABASES}."
    )

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = os.getenv("DEMO_ACCOUNTS_PASSWORD", secrets.token_urlsafe(16))

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

def clean_and_signup():
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    print("=" * 75)
    print("  SIGNING UP TEST ACCOUNTS IN NON-PRODUCTION ENVIRONMENT  ")
    print("=" * 75)

    with engine.connect() as conn:
        for acc in ACCOUNTS:
            email = acc["email"]
            signup_url = f"{SUPABASE_URL}/auth/v1/signup"
            payload = {
                "email": email,
                "password": TEST_PASSWORD,
                "data": {"full_name": acc["full_name"], "role": acc["role"]}
            }
            resp = requests.post(signup_url, json=payload, headers=headers)
            print(f"  • {email} signup: {resp.status_code}")

if __name__ == "__main__":
    clean_and_signup()
