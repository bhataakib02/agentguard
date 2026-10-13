import os
import secrets
import requests
import time
from database import SessionLocal
from config import settings
import models

if settings.ENVIRONMENT == "production":
    raise RuntimeError(
        "[AgentGuard Security Block] create_test_accounts script cannot be executed in PRODUCTION."
    )

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = os.getenv("DEMO_ACCOUNTS_PASSWORD", secrets.token_urlsafe(16))

ACCOUNTS = [
    {"email": "user@agentguard.com", "full_name": "User Account", "role": "USER", "department": "General"},
    {"email": "viewer@agentguard.com", "full_name": "Viewer Account", "role": "VIEWER", "department": "Analytics"},
    {"email": "analyst@agentguard.com", "full_name": "Analyst Account", "role": "ANALYST", "department": "AI Governance"},
    {"email": "operator@agentguard.com", "full_name": "Operator Account", "role": "OPERATOR", "department": "Runtime Operations"},
    {"email": "security.analyst@agentguard.com", "full_name": "Security Analyst Account", "role": "SECURITY_ANALYST", "department": "SOC & Incident Response"},
    {"email": "manager@agentguard.com", "full_name": "Manager Account", "role": "MANAGER", "department": "Operations Management"},
    {"email": "developer@agentguard.com", "full_name": "Developer Account", "role": "DEVELOPER", "department": "Engineering"},
    {"email": "admin@agentguard.com", "full_name": "Admin Account", "role": "ADMIN", "department": "Administration"},
    {"email": "superadmin@agentguard.com", "full_name": "Super Admin Account", "role": "SUPER_ADMIN", "department": "Executive Leadership"}
]

def setup_supabase_auth_accounts():
    db = SessionLocal()
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    org = db.query(models.Organization).first()
    if not org:
        org = models.Organization(name="AgentGuard Test Corp")
        db.add(org)
        db.commit()
        db.refresh(org)

    for acc in ACCOUNTS:
        email = acc["email"]
        resp = requests.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            json={"email": email, "password": TEST_PASSWORD},
            headers=headers
        )
        print(f"Provisioned {email}: {resp.status_code}")
    db.close()

if __name__ == "__main__":
    setup_supabase_auth_accounts()
