import os
import json
import uuid
import datetime
import passlib.hash
import requests
from sqlalchemy import text

import sys
sys.path.insert(0, r"d:\AGENTGUARD\backend")

from database import engine
from config import settings

DATASET_DIR = r"d:\AGENTGUARD\AGENTGUARD_5_ORGANIZATIONS_DATASET"
TEST_PASSWORD = "Blackbird@12."

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
    {"id": "user-040", "org_id": "org-005", "name": "Vihaan Singh", "role": "ADMIN", "email": "vihaan@edunova.com"}
]

def update_users_json():
    print("1. Updating AGENTGUARD_5_ORGANIZATIONS_DATASET/users.json...")
    users_json_path = os.path.join(DATASET_DIR, "users.json")
    
    new_users_data = []
    for u in DOCX_USER_TABLES:
        new_users_data.append({
            "id": u["id"],
            "organization_id": u["org_id"],
            "full_name": u["name"],
            "email": u["email"],
            "role": u["role"],
            "status": "ACTIVE",
            "email_verified": True,
            "created_at": "2026-01-02T00:00:00+00:00",
            "last_login": "2026-08-31T00:00:00+00:00"
        })

    with open(users_json_path, "w", encoding="utf-8") as f:
        json.dump(new_users_data, f, indent=2)
    print("   [SUCCESS] users.json updated with exact DOCX test emails!")

def update_database_users():
    print("\n2. Updating Supabase Auth & Public Users in Database...")
    headers = {
        "apikey": settings.SUPABASE_PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }

    with engine.connect() as conn:
        sa_hash = conn.execute(text("SELECT encrypted_password FROM auth.users WHERE email = 'thefreelancer2076@gmail.com';")).scalar()

        # Delete non-superadmin demo accounts that were old emails
        old_emails = [u["email"] for u in DOCX_USER_TABLES]
        conn.execute(
            text("DELETE FROM public.users WHERE email <> 'thefreelancer2076@gmail.com' AND email NOT IN :emails;"),
            {"emails": tuple(old_emails)}
        )
        conn.execute(
            text("DELETE FROM auth.users WHERE email <> 'thefreelancer2076@gmail.com' AND email NOT IN :emails;"),
            {"emails": tuple(old_emails)}
        )
        conn.commit()

        for u in DOCX_USER_TABLES:
            email = u["email"]
            name = u["name"]
            role = u["role"]
            orig_id = u["id"]
            pub_u_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user-{orig_id}"))
            mapped_org = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"org-{u['org_id']}"))

            # 1. Upsert auth.users
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
                    {"email": email, "hash": sa_hash}
                )
                existing_auth = conn.execute(text("SELECT id FROM auth.users WHERE email = :email;"), {"email": email}).first()

            auth_id_str = str(existing_auth.id)

            conn.execute(
                text("UPDATE auth.users SET encrypted_password = :hash, email_confirmed_at = NOW(), raw_user_meta_data = CAST(:meta AS jsonb) WHERE id = :id;"),
                {
                    "hash": sa_hash,
                    "id": auth_id_str,
                    "meta": json.dumps({"sub": auth_id_str, "email": email, "full_name": name, "email_verified": True})
                }
            )

            # 2. Upsert auth.identities
            existing_id = conn.execute(text("SELECT id FROM auth.identities WHERE user_id = :u_id;"), {"u_id": auth_id_str}).first()
            id_data = json.dumps({"sub": auth_id_str, "email": email, "email_verified": True})
            if not existing_id:
                conn.execute(
                    text("""
                        INSERT INTO auth.identities (
                            id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
                        ) VALUES (
                            gen_random_uuid(), :u_id, CAST(:id_data AS jsonb), 'email', :email, NOW(), NOW(), NOW()
                        );
                    """),
                    {"u_id": auth_id_str, "id_data": id_data, "email": email}
                )

            # 3. Upsert public.users
            dept_map = {
                "ADMIN": "Administration", "MANAGER": "Management", "SECURITY_ANALYST": "Security SOC",
                "OPERATOR": "Operations", "ANALYST": "Analytics", "DEVELOPER": "Engineering",
                "VIEWER": "Governance", "USER": "General"
            }
            dept = dept_map.get(role, "General")

            conn.execute(
                text("""
                    INSERT INTO public.users (
                        id, org_id, auth_user_id, email, full_name, role, department, status, created_at, updated_at
                    ) VALUES (
                        :id, :org_id, :auth_id, :email, :name, :role, :dept, 'ACTIVE', NOW(), NOW()
                    ) ON CONFLICT (id) DO UPDATE 
                    SET org_id = EXCLUDED.org_id, auth_user_id = EXCLUDED.auth_user_id, email = EXCLUDED.email, full_name = EXCLUDED.full_name, role = EXCLUDED.role, status = 'ACTIVE';
                """),
                {
                    "id": pub_u_id,
                    "org_id": mapped_org,
                    "auth_id": auth_id_str,
                    "email": email,
                    "name": name,
                    "role": role,
                    "dept": dept
                }
            )
        conn.commit()
        print("   [SUCCESS] All 40 DOCX tenant user accounts updated in Auth & Public DB!")

    print("\n3. Testing Real Supabase Authentication for DOCX Accounts...")
    login_url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
    
    test_logins = [
        "zoya@acme.com", "aarav@acme.com", "kabir@nexa.com", "ira@medcore.com",
        "vihaan@urbangrid.com", "anaya@edunova.com", "thefreelancer2076@gmail.com"
    ]

    for em in test_logins:
        resp = requests.post(login_url, json={"email": em, "password": TEST_PASSWORD}, headers=headers)
        if resp.status_code == 200:
            print(f"   • {em:<35} | PASS (200 OK)")
        else:
            print(f"   • {em:<35} | FAIL ({resp.status_code}): {resp.text}")

if __name__ == "__main__":
    update_users_json()
    update_database_users()
