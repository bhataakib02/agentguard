import os
import json
import uuid
import datetime
import passlib.hash
import requests
import secrets
from sqlalchemy import text

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import engine
from config import settings

if settings.ENVIRONMENT == "production":
    raise RuntimeError(
        "[AgentGuard Security Block] update_and_seed_docx_users script cannot be executed in PRODUCTION."
    )

TEST_PASSWORD = os.getenv("DEMO_ACCOUNTS_PASSWORD", secrets.token_urlsafe(16))

DOCX_USER_TABLES = [
    # Org 1: ACME Technologies (org-001)
    {"id": "user-001", "org_id": "org-001", "name": "Zoya Khan", "role": "USER", "email": "zoya@acme.com"},
    {"id": "user-002", "org_id": "org-001", "name": "Kabir Mehta", "role": "VIEWER", "email": "kabir@acme.com"},
    {"id": "user-003", "org_id": "org-001", "name": "Ira Patel", "role": "ANALYST", "email": "ira@acme.com"},
    {"id": "user-004", "org_id": "org-001", "name": "Vihaan Singh", "role": "OPERATOR", "email": "vihaan@acme.com"},
    {"id": "user-005", "org_id": "org-001", "name": "Anaya Bhat", "role": "SECURITY_ANALYST", "email": "anaya@acme.com"},
    {"id": "user-006", "org_id": "org-001", "name": "Arjun Verma", "role": "MANAGER", "email": "arjun@acme.com"},
    {"id": "user-007", "org_id": "org-001", "name": "Meera Nair", "role": "DEVELOPER", "email": "meera@acme.com"},
    {"id": "user-008", "org_id": "org-001", "name": "Aarav Sharma", "role": "ADMIN", "email": "aarav@acme.com"},

    # Org 2: Nexa Financial Services (org-002)
    {"id": "user-009", "org_id": "org-002", "name": "Kabir Mehta", "role": "USER", "email": "kabir@nexa.com"},
    {"id": "user-010", "org_id": "org-002", "name": "Ira Patel", "role": "VIEWER", "email": "ira@nexa.com"},
    {"id": "user-011", "org_id": "org-002", "name": "Vihaan Singh", "role": "ANALYST", "email": "vihaan@nexa.com"},
    {"id": "user-012", "org_id": "org-002", "name": "Anaya Bhat", "role": "OPERATOR", "email": "anaya@nexa.com"},
    {"id": "user-013", "org_id": "org-002", "name": "Arjun Verma", "role": "SECURITY_ANALYST", "email": "arjun@nexa.com"},
    {"id": "user-014", "org_id": "org-002", "name": "Meera Nair", "role": "MANAGER", "email": "meera@nexa.com"},
    {"id": "user-015", "org_id": "org-002", "name": "Aarav Sharma", "role": "DEVELOPER", "email": "aarav@nexa.com"},
    {"id": "user-016", "org_id": "org-002", "name": "Zoya Khan", "role": "ADMIN", "email": "zoya@nexa.com"},

    # Org 3: MedCore Health Systems (org-003)
    {"id": "user-017", "org_id": "org-003", "name": "Ira Patel", "role": "USER", "email": "ira@medcore.com"},
    {"id": "user-018", "org_id": "org-003", "name": "Vihaan Singh", "role": "VIEWER", "email": "vihaan@medcore.com"},
    {"id": "user-019", "org_id": "org-003", "name": "Anaya Bhat", "role": "ANALYST", "email": "anaya@medcore.com"},
    {"id": "user-020", "org_id": "org-003", "name": "Arjun Verma", "role": "OPERATOR", "email": "arjun@medcore.com"},
    {"id": "user-021", "org_id": "org-003", "name": "Meera Nair", "role": "SECURITY_ANALYST", "email": "meera@medcore.com"},
    {"id": "user-022", "org_id": "org-003", "name": "Aarav Sharma", "role": "MANAGER", "email": "aarav@medcore.com"},
    {"id": "user-023", "org_id": "org-003", "name": "Zoya Khan", "role": "DEVELOPER", "email": "zoya@medcore.com"},
    {"id": "user-024", "org_id": "org-003", "name": "Kabir Mehta", "role": "ADMIN", "email": "kabir@medcore.com"},

    # Org 4: UrbanGrid Logistics (org-004)
    {"id": "user-025", "org_id": "org-004", "name": "Vihaan Singh", "role": "USER", "email": "vihaan@urbangrid.com"},
    {"id": "user-026", "org_id": "org-004", "name": "Anaya Bhat", "role": "VIEWER", "email": "anaya@urbangrid.com"},
    {"id": "user-027", "org_id": "org-004", "name": "Arjun Verma", "role": "ANALYST", "email": "arjun@urbangrid.com"},
    {"id": "user-028", "org_id": "org-004", "name": "Meera Nair", "role": "OPERATOR", "email": "meera@urbangrid.com"},
    {"id": "user-029", "org_id": "org-004", "name": "Aarav Sharma", "role": "SECURITY_ANALYST", "email": "aarav@urbangrid.com"},
    {"id": "user-030", "org_id": "org-004", "name": "Zoya Khan", "role": "MANAGER", "email": "zoya@urbangrid.com"},
    {"id": "user-031", "org_id": "org-004", "name": "Kabir Mehta", "role": "DEVELOPER", "email": "kabir@urbangrid.com"},
    {"id": "user-032", "org_id": "org-004", "name": "Ira Patel", "role": "ADMIN", "email": "ira@urbangrid.com"},

    # Org 5: EduNova Learning (org-005)
    {"id": "user-033", "org_id": "org-005", "name": "Anaya Bhat", "role": "USER", "email": "anaya@edunova.com"},
    {"id": "user-034", "org_id": "org-005", "name": "Arjun Verma", "role": "VIEWER", "email": "arjun@edunova.com"},
    {"id": "user-035", "org_id": "org-005", "name": "Meera Nair", "role": "ANALYST", "email": "meera@edunova.com"},
    {"id": "user-036", "org_id": "org-005", "name": "Aarav Sharma", "role": "OPERATOR", "email": "aarav@edunova.com"},
    {"id": "user-037", "org_id": "org-005", "name": "Zoya Khan", "role": "SECURITY_ANALYST", "email": "zoya@edunova.com"},
    {"id": "user-038", "org_id": "org-005", "name": "Kabir Mehta", "role": "MANAGER", "email": "kabir@edunova.com"},
    {"id": "user-039", "org_id": "org-005", "name": "Ira Patel", "role": "DEVELOPER", "email": "ira@edunova.com"},
    {"id": "user-040", "org_id": "org-005", "name": "Vihaan Singh", "role": "ADMIN", "email": "vihaan@edunova.com"},
]

def seed_demo_users_nonprod():
    if os.getenv("ALLOW_DEMO_SEED", "false").lower() not in ("true", "1"):
        print("[AgentGuard Safety Block] Demo user seeding is disabled. Set ALLOW_DEMO_SEED=true to proceed.")
        return

    pwd_hash = passlib.hash.bcrypt.hash(TEST_PASSWORD)
    with engine.connect() as conn:
        for u in DOCX_USER_TABLES:
            email = u["email"]
            name = u["name"]
            role = u["role"]
            mapped_org = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"org-{u['org_id']}"))

            existing_user = conn.execute(text("SELECT id FROM public.users WHERE email = :email;"), {"email": email}).first()
            if not existing_user:
                conn.execute(
                    text("""
                        INSERT INTO public.users (id, org_id, email, full_name, role, status, password_hash)
                        VALUES (gen_random_uuid(), :org_id, :email, :name, :role, 'ACTIVE', :pwd);
                    """),
                    {"org_id": mapped_org, "email": email, "name": name, "role": role, "pwd": pwd_hash}
                )
        conn.commit()
    print("Non-production demo users verified.")

if __name__ == "__main__":
    seed_demo_users_nonprod()
