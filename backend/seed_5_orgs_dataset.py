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

def load_json(filename):
    path = os.path.join(DATASET_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_dt(val):
    if not val:
        return datetime.datetime.utcnow()
    try:
        if "T" in str(val):
            return datetime.datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return datetime.datetime.strptime(str(val), "%Y-%m-%d")
    except Exception:
        return datetime.datetime.utcnow()

def seed_dataset():
    print("=" * 75)
    print("  SEEDING 5-ORGANIZATION DATASET WITH DOCX TESTING CREDENTIALS  ")
    print("=" * 75)

    # Update users.json
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

    # Read dataset JSONs
    orgs_data = load_json("organizations.json")
    licenses_data = load_json("licenses.json")
    users_data = new_users_data
    agents_data = load_json("agents.json")
    passports_data = load_json("agent_passports.json")
    tokens_data = load_json("capability_tokens.json")
    policies_data = load_json("policies.json")
    decisions_data = load_json("decisions.json")
    approvals_data = load_json("approval_requests.json")
    audits_data = load_json("audit_logs.json")
    security_data = load_json("security_events.json")
    notifications_data = load_json("notifications.json")

    # Mappings from short string IDs to UUID strings
    org_map = {}
    user_map = {}
    agent_map = {}
    decision_map = {}

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 0. Clean old tenant data first (preserve Super Admin)
            print("0. Cleaning old tenant data while preserving Super Admin...")
            sa_hash = conn.execute(text("SELECT encrypted_password FROM auth.users WHERE email = 'thefreelancer2076@gmail.com';")).scalar()

            conn.execute(text("UPDATE public.users SET org_id = NULL WHERE email = 'thefreelancer2076@gmail.com';"))
            
            tables_to_purge = [
                'provenance_events', 'approval_requests', 'decisions', 'capability_tokens',
                'permissions', 'agent_passports', 'agent_credentials', 'risk_scores',
                'behavior_profiles', 'reputation_scores', 'circuit_breakers', 'budgets',
                'transactions', 'security_tests', 'simulations', 'resource_usages',
                'anomaly_events', 'security_incidents', 'agent_relationships', 'agents',
                'policy_rules', 'policies', 'audit_logs', 'notifications', 'sessions',
                'api_keys', 'report_histories', 'scheduled_reports', 'license_usages', 'licenses'
            ]
            for tbl in tables_to_purge:
                conn.execute(text(f"DELETE FROM public.{tbl};"))

            conn.execute(text("DELETE FROM public.users WHERE email <> 'thefreelancer2076@gmail.com';"))
            conn.execute(text("DELETE FROM public.organizations;"))

            conn.execute(text("DELETE FROM auth.refresh_tokens;"))
            conn.execute(text("DELETE FROM auth.sessions;"))
            conn.execute(text("DELETE FROM auth.identities WHERE email <> 'thefreelancer2076@gmail.com';"))
            conn.execute(text("DELETE FROM auth.users WHERE email <> 'thefreelancer2076@gmail.com';"))

            print("   [CLEANED] Old tenant data purged.")

            # 1. ORGANIZATIONS & LICENSES & USAGES
            print(f"1. Seeding {len(orgs_data)} Organizations & Licenses...")
            for o in orgs_data:
                orig_id = o["id"]
                u_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"org-{orig_id}"))
                org_map[orig_id] = u_id

                conn.execute(
                    text("""
                        INSERT INTO public.organizations (id, name, slug, status, created_at)
                        VALUES (:id, :name, :slug, :status, :created_at);
                    """),
                    {
                        "id": u_id,
                        "name": o["name"],
                        "slug": o.get("slug", o["name"].lower().replace(" ", "-")),
                        "status": o.get("status", "ACTIVE"),
                        "created_at": parse_dt(o.get("created_at"))
                    }
                )

            for lic in licenses_data:
                lic_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"lic-{lic['id']}"))
                mapped_org = org_map[lic["organization_id"]]
                conn.execute(
                    text("""
                        INSERT INTO public.licenses (
                            id, org_id, plan_id, status, start_date, expiry_date, max_users, max_ai_agents, max_api_keys, max_monthly_api_requests, max_storage_gb
                        ) VALUES (
                            :id, :org_id, :plan_id, :status, :start_date, :expiry_date, :max_users, :max_ai_agents, 10, 500000, 100.0
                        );
                    """),
                    {
                        "id": lic_id,
                        "org_id": mapped_org,
                        "plan_id": lic.get("license_type", "ENTERPRISE"),
                        "status": lic.get("status", "ACTIVE"),
                        "start_date": parse_dt(lic.get("start_date")),
                        "expiry_date": parse_dt(lic.get("expiry_date")),
                        "max_users": lic.get("seat_limit", 50),
                        "max_ai_agents": lic.get("agent_limit", 100)
                    }
                )

                conn.execute(
                    text("""
                        INSERT INTO public.license_usages (id, org_id, api_requests_count, storage_used_gb, last_calculated_at)
                        VALUES (:id, :org_id, 1250, 1.5, NOW());
                    """),
                    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"usage-{lic['id']}")), "org_id": mapped_org}
                )

            # 2. USERS (AUTH.USERS & PUBLIC.USERS)
            print(f"2. Seeding {len(users_data)} DOCX Users into Auth & Public DB...")
            for u in users_data:
                orig_id = u["id"]
                pub_u_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user-{orig_id}"))
                user_map[orig_id] = pub_u_id

                email = u["email"]
                role = u["role"]
                full_name = u["full_name"]
                mapped_org = org_map[u["organization_id"]]

                auth_u_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"auth-{orig_id}-{email}"))

                # Insert into auth.users with empty string tokens and NULL super admin flag
                conn.execute(
                    text("""
                        INSERT INTO auth.users (
                            id, instance_id, aud, role, email, encrypted_password, email_confirmed_at,
                            raw_app_meta_data, raw_user_meta_data, created_at, updated_at, is_super_admin,
                            confirmation_token, recovery_token, email_change_token_new, email_change, phone_change
                        ) VALUES (
                            :id, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
                            :email, :hash, NOW(), '{"provider":"email","providers":["email"]}', CAST(:meta AS jsonb), NOW(), NOW(), NULL,
                            '', '', '', '', ''
                        );
                    """),
                    {
                        "id": auth_u_id,
                        "email": email,
                        "hash": sa_hash,
                        "meta": json.dumps({"sub": auth_u_id, "email": email, "full_name": full_name, "email_verified": True})
                    }
                )

                # Insert into auth.identities matching provider_id = auth_u_id and id = auth_u_id
                id_data = json.dumps({"sub": auth_u_id, "email": email, "email_verified": True})
                conn.execute(
                    text("""
                        INSERT INTO auth.identities (
                            id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
                        ) VALUES (
                            :u_id, :u_id, CAST(:id_data AS jsonb), 'email', :u_id_str, NOW(), NOW(), NOW()
                        );
                    """),
                    {"u_id": auth_u_id, "u_id_str": auth_u_id, "id_data": id_data}
                )

                # Insert into public.users
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
                        );
                    """),
                    {
                        "id": pub_u_id,
                        "org_id": mapped_org,
                        "auth_id": auth_u_id,
                        "email": email,
                        "name": full_name,
                        "role": role,
                        "dept": dept
                    }
                )

            # 3. AGENTS & PASSPORTS
            print(f"3. Seeding {len(agents_data)} Agents & {len(passports_data)} Passports...")
            for idx, a in enumerate(agents_data):
                orig_id = a["id"]
                ag_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"agent-{orig_id}"))
                agent_map[orig_id] = ag_uuid

                mapped_org = org_map[a["organization_id"]]
                mapped_owner = user_map.get(a.get("owner_user_id"), list(user_map.values())[0])
                risk_val = 75 if a.get("risk_level") == "HIGH" else (45 if a.get("risk_level") == "MEDIUM" else 15)

                conn.execute(
                    text("""
                        INSERT INTO public.agents (
                            id, agent_code, org_id, owner_id, name, department, purpose, model_name, model_version, environment, autonomy_level, status, risk_score, trust_score, daily_budget, created_at
                        ) VALUES (
                            :id, :code, :org_id, :owner_id, :name, 'Operations', :purpose, 'gpt-4o', '1.0.0', 'PRODUCTION', :autonomy, :status, :risk_score, 95, 10000.0, NOW()
                        );
                    """),
                    {
                        "id": ag_uuid,
                        "code": f"AG-{100 + idx + 1}",
                        "org_id": mapped_org,
                        "owner_id": mapped_owner,
                        "name": a["name"],
                        "purpose": a.get("purpose", "Synthetic AI Agent Workflow"),
                        "autonomy": a.get("autonomy_level", "MEDIUM"),
                        "status": a.get("status", "NORMAL"),
                        "risk_score": risk_val
                    }
                )

            for pass_item in passports_data:
                pass_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"passport-{pass_item['id']}"))
                mapped_agent = agent_map[pass_item["agent_id"]]
                conn.execute(
                    text("""
                        INSERT INTO public.agent_passports (
                            id, agent_id, passport_number, digital_signature, issued_at, expires_at, verification_status
                        ) VALUES (
                            :id, :agent_id, :pass_num, :sig, NOW(), NOW() + INTERVAL '365 days', 'VERIFIED'
                        );
                    """),
                    {
                        "id": pass_uuid,
                        "agent_id": mapped_agent,
                        "pass_num": f"PASSPORT-{pass_item['id']}",
                        "sig": f"SIG-SHA256-AGENTGUARD-{pass_item['id']}"
                    }
                )

            # 4. CAPABILITY TOKENS
            print(f"4. Seeding {len(tokens_data)} Capability Tokens...")
            for tok in tokens_data:
                tok_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"token-{tok['id']}"))
                mapped_agent = agent_map[tok["agent_id"]]
                conn.execute(
                    text("""
                        INSERT INTO public.capability_tokens (
                            id, token_code, agent_id, capability_name, scope, amount_limit, issued_at, expires_at, status
                        ) VALUES (
                            :id, :code, :agent_id, :cap_name, :scope, 5000.0, :issued_at, :expires_at, :status
                        );
                    """),
                    {
                        "id": tok_uuid,
                        "code": f"CAP-{tok['id']}",
                        "agent_id": mapped_agent,
                        "cap_name": tok.get("capability", "customer_data:read"),
                        "scope": tok.get("scope", "global"),
                        "issued_at": parse_dt(tok.get("issued_at")),
                        "expires_at": parse_dt(tok.get("expires_at")),
                        "status": tok.get("status", "ACTIVE")
                    }
                )

            # 5. POLICIES & RULES
            print(f"5. Seeding {len(policies_data)} Policies & Rules...")
            for pol in policies_data:
                pol_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"policy-{pol['id']}"))
                mapped_org = org_map[pol["organization_id"]]

                conn.execute(
                    text("""
                        INSERT INTO public.policies (id, org_id, name, category, priority, status, version, created_at)
                        VALUES (:id, :org_id, :name, 'GOVERNANCE', 1, :status, '1.0.0', NOW());
                    """),
                    {
                        "id": pol_uuid,
                        "org_id": mapped_org,
                        "name": pol["name"],
                        "status": pol.get("status", "ACTIVE")
                    }
                )

                rule_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"rule-{pol['id']}"))
                conn.execute(
                    text("""
                        INSERT INTO public.policy_rules (id, policy_id, condition_expression, decision_output, risk_delta, description)
                        VALUES (:id, :policy_id, 'risk_score > 50', 'REVIEW', 20, :desc);
                    """),
                    {
                        "id": rule_uuid,
                        "policy_id": pol_uuid,
                        "desc": pol.get("rule", "Standard governance rule evaluation")
                    }
                )

            # 6. DECISIONS
            print(f"6. Seeding {len(decisions_data)} Governance Decisions...")
            for d in decisions_data:
                dec_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"decision-{d['id']}"))
                decision_map[d["id"]] = dec_uuid
                mapped_agent = agent_map[d["agent_id"]]

                conn.execute(
                    text("""
                        INSERT INTO public.decisions (
                            id, agent_id, user_id, intent_summary, action_requested, resource_target, amount, decision, risk_score, policy_name, explanation, execution_status, timestamp
                        ) VALUES (
                            :id, :agent_id, NULL, :intent, :action, 'data_warehouse', 0.0, :decision, :risk_score, 'Data Access Policy', :explanation, 'EXECUTED', :created_at
                        );
                    """),
                    {
                        "id": dec_uuid,
                        "agent_id": mapped_agent,
                        "intent": f"Requested action: {d.get('requested_action', 'api_access')}",
                        "action": d.get("requested_action", "api_access"),
                        "decision": d.get("governance_outcome", "ALLOW"),
                        "risk_score": d.get("risk_score", 20),
                        "explanation": f"Governance evaluation result: {d.get('governance_outcome', 'ALLOW')}",
                        "created_at": parse_dt(d.get("created_at"))
                    }
                )

            # 7. APPROVAL REQUESTS
            print(f"7. Seeding {len(approvals_data)} Approval Requests...")
            for app in approvals_data:
                app_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"approval-{app['id']}"))
                mapped_agent = agent_map[app["agent_id"]]
                mapped_user = user_map.get(app.get("requester_user_id"), list(user_map.values())[0])

                first_dec = list(decision_map.values())[0] if decision_map else str(uuid.uuid4())

                conn.execute(
                    text("""
                        INSERT INTO public.approval_requests (
                            id, decision_id, agent_id, approver_id, amount, reason, status, created_at
                        ) VALUES (
                            :id, :dec_id, :agent_id, :approver_id, 2500.0, :reason, :status, :created_at
                        );
                    """),
                    {
                        "id": app_uuid,
                        "dec_id": first_dec,
                        "agent_id": mapped_agent,
                        "approver_id": mapped_user,
                        "reason": f"Approval requested for {app.get('action', 'sensitive_operation')}",
                        "status": app.get("status", "PENDING"),
                        "created_at": parse_dt(app.get("created_at"))
                    }
                )

            # 8. AUDIT LOGS
            print(f"8. Seeding {len(audits_data)} Audit Logs...")
            for aud in audits_data:
                aud_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"audit-{aud['id']}"))
                actor = user_map.get(aud.get("actor_user_id"), "SYSTEM_ADMIN")

                conn.execute(
                    text("""
                        INSERT INTO public.audit_logs (
                            id, event_type, actor_type, actor_id, action, resource, result, metadata_json, timestamp
                        ) VALUES (
                            :id, 'DATASET_AUDIT', 'USER', :actor_id, :action, :resource, 'SUCCESS', '{}'::jsonb, :timestamp
                        );
                    """),
                    {
                        "id": aud_uuid,
                        "actor_id": str(actor),
                        "action": aud.get("action", "PLATFORM_ACCESS"),
                        "resource": aud.get("target_type", "GENERAL"),
                        "timestamp": parse_dt(aud.get("timestamp"))
                    }
                )

            # 9. SECURITY INCIDENTS / EVENTS
            print(f"9. Seeding {len(security_data)} Security Events...")
            for sec in security_data:
                sec_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"security-{sec['id']}"))
                mapped_org = org_map[sec["organization_id"]]

                conn.execute(
                    text("""
                        INSERT INTO public.security_incidents (
                            id, org_id, agent_id, title, severity, status, timeline_json, created_at
                        ) VALUES (
                            :id, :org_id, NULL, :title, :severity, :status, '[]'::jsonb, :created_at
                        );
                    """),
                    {
                        "id": sec_uuid,
                        "org_id": mapped_org,
                        "title": sec.get("type", "SECURITY_ALERT"),
                        "severity": sec.get("severity", "MEDIUM"),
                        "status": sec.get("status", "OPEN"),
                        "created_at": parse_dt(sec.get("created_at"))
                    }
                )

            # 10. NOTIFICATIONS
            print(f"10. Seeding {len(notifications_data)} Notifications...")
            for notif in notifications_data:
                notif_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"notif-{notif['id']}"))
                mapped_user = list(user_map.values())[0]

                conn.execute(
                    text("""
                        INSERT INTO public.notifications (
                            id, user_id, type, title, message, severity, is_read, created_at
                        ) VALUES (
                            :id, :user_id, :type, 'System Alert', :msg, 'INFO', false, NOW()
                        );
                    """),
                    {
                        "id": notif_uuid,
                        "user_id": mapped_user,
                        "type": notif.get("type", "ALERT"),
                        "msg": notif.get("message", "System notification event")
                    }
                )

            trans.commit()
            print("\n[SUCCESS] 5-Organization Dataset fully seeded into Supabase PostgreSQL!")

        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Transaction failed: {e}")
            raise e

    # Test logins
    print("\nTesting Real Supabase Authentication for DOCX Accounts...")
    headers = {
        "apikey": settings.SUPABASE_PUBLISHABLE_KEY,
        "Content-Type": "application/json"
    }
    login_url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
    
    test_logins = [
        ("ACME USER", "zoya@acme.com"),
        ("ACME ADMIN", "aarav@acme.com"),
        ("NEXA USER", "kabir@nexa.com"),
        ("MEDCORE USER", "ira@medcore.com"),
        ("URBANGRID USER", "vihaan@urbangrid.com"),
        ("EDUNOVA USER", "anaya@edunova.com"),
        ("SUPER ADMIN", "thefreelancer2076@gmail.com")
    ]

    for label, em in test_logins:
        resp = requests.post(login_url, json={"email": em, "password": TEST_PASSWORD}, headers=headers)
        if resp.status_code == 200:
            print(f"   • {label:<16} | {em:<35} | PASS (200 OK Token Granted)")
        else:
            print(f"   • {label:<16} | {em:<35} | FAIL ({resp.status_code}): {resp.text}")

if __name__ == "__main__":
    seed_dataset()
