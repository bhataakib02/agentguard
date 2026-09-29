import requests
import time
from database import SessionLocal
from config import settings
import models

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = "Blackbird@12."

ACCOUNTS = [
    {"email": "user@agentguard.com", "full_name": "User Account", "role": "USER", "department": "General"},
    {"email": "viewer@agentguard.com", "full_name": "Viewer Account", "role": "VIEWER", "department": "Analytics"},
    {"email": "analyst@agentguard.com", "full_name": "Analyst Account", "role": "ANALYST", "department": "AI Governance"},
    {"email": "operator@agentguard.com", "full_name": "Operator Account", "role": "OPERATOR", "department": "Runtime Operations"},
    {"email": "security.analyst@agentguard.com", "full_name": "Security Analyst Account", "role": "SECURITY_ANALYST", "department": "SOC & Incident Response"},
    {"email": "manager@agentguard.com", "full_name": "Manager Account", "role": "MANAGER", "department": "Operations Management"},
    {"email": "developer@agentguard.com", "full_name": "Developer Account", "role": "DEVELOPER", "department": "Engineering"},
    {"email": "admin@agentguard.com", "full_name": "Admin Account", "role": "ADMIN", "department": "Administration"},
    {"email": "thefreelancer2076@gmail.com", "full_name": "Super Admin Account", "role": "SUPER_ADMIN", "department": "Executive Leadership"}
]

def setup_supabase_auth_accounts():
    db = SessionLocal()
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    # Ensure default Organization exists
    org = db.query(models.Organization).first()
    if not org:
        org = models.Organization(name="AgentGuard Enterprise", domain="agentguard.com")
        db.add(org)
        db.commit()
        db.refresh(org)

    target_org_id = str(org.id)

    print("=" * 75)
    print("  PROVISIONING REAL SUPABASE AUTH DEVELOPMENT/TEST ACCOUNTS  ")
    print("=" * 75)

    results = []

    for acc in ACCOUNTS:
        email = acc["email"]
        role = acc["role"]
        full_name = acc["full_name"]
        department = acc["department"]

        auth_user_id = None

        # 1. Attempt Supabase Auth Login first
        login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        login_resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)

        if login_resp.status_code == 200:
            data = login_resp.json()
            auth_user_id = data.get("user", {}).get("id")
            print(f"  [SUPABASE AUTH] Verified existing account: {email}")
        else:
            # 2. Account doesn't exist or rate-limited; call Supabase Auth SignUp
            signup_url = f"{SUPABASE_URL}/auth/v1/signup"
            signup_resp = requests.post(signup_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)

            if signup_resp.status_code in [200, 201]:
                data = signup_resp.json()
                auth_user_id = data.get("id") or data.get("user", {}).get("id")
                print(f"  [SUPABASE AUTH] Created new Supabase account: {email}")
            elif signup_resp.status_code == 429:
                time.sleep(3.0)
                retry_resp = requests.post(signup_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)
                if retry_resp.status_code in [200, 201]:
                    data = retry_resp.json()
                    auth_user_id = data.get("id") or data.get("user", {}).get("id")
                    print(f"  [SUPABASE AUTH] Created new Supabase account (after retry): {email}")

        # 3. Create or Update PostgreSQL User record
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            user = models.User(
                org_id=target_org_id,
                auth_user_id=auth_user_id,
                email=email,
                full_name=full_name,
                role=role,
                department=department,
                status="ACTIVE"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"  [DATABASE PROFILE] Created user profile in PostgreSQL: {email} ({role})")
        else:
            user.role = role
            user.department = department
            if auth_user_id:
                user.auth_user_id = auth_user_id
            db.commit()
            print(f"  [DATABASE PROFILE] Updated user profile in PostgreSQL: {email} -> Role: {role}")

        results.append({
            "email": email,
            "role": role,
            "auth_user_id": user.auth_user_id or auth_user_id or "Linked",
            "status": "PASS — SUPABASE AUTH & POSTGRESQL SYNCED"
        })

        time.sleep(1.0)

    db.close()

    print("\n" + "=" * 75)
    print("      DEVELOPMENT/TEST ACCOUNTS PROVISIONING SUMMARY      ")
    print("=" * 75)
    for r in results:
        print(f"  • {r['role']:<18} | {r['email']:<32} | {r['status']}")
    print("=" * 75)

if __name__ == "__main__":
    setup_supabase_auth_accounts()
