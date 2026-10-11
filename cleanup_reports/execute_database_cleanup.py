import sys
import os
import json
import datetime
from sqlalchemy import text, inspect

sys.path.insert(0, r"d:\AGENTGUARD\backend")
from database import engine

GENUINE_ORG_IDS = (
    '8b79cca4-9cbf-4969-920e-e433ddc2808f', # Platform Admin Control
    '08498fe0-2565-45c3-9a49-57e4c0c3cb44', # AgentGuard Enterprise Core
)

GENUINE_USER_EMAILS = (
    'thefreelancer2076@gmail.com',
    'suite_user@agentguard.com',
    'suite_admin@agentguard.com',
    'suite_super_admin@agentguard.com',
    'suite_developer@agentguard.com',
    'suite_operator@agentguard.com',
    'suite_analyst@agentguard.com',
    'suite_manager@agentguard.com',
    'suite_security_analyst@agentguard.com',
    'suite_viewer@agentguard.com'
)

def execute_cleanup():
    print("=" * 75)
    print("  EXECUTING AGENTGUARD AUTHORITATIVE DATABASE CLEANUP")
    print("=" * 75)

    stats = {}

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Disassociate dummy org_id from audit_logs to preserve 100% audit records without FK violation
            res = conn.execute(text("""
                UPDATE audit_logs
                SET org_id = NULL
                WHERE org_id IS NOT NULL AND org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["audit_logs_disassociated"] = res.rowcount
            stats["audit_logs_deleted"] = 0

            # 2. Webhook deliveries
            res = conn.execute(text("""
                DELETE FROM webhook_deliveries
                WHERE webhook_id IN (
                    SELECT id FROM webhook_endpoints WHERE org_id NOT IN :org_ids
                )
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["webhook_deliveries"] = res.rowcount

            # 3. Webhook endpoints
            res = conn.execute(text("""
                DELETE FROM webhook_endpoints WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["webhook_endpoints"] = res.rowcount

            # 4. Policy rules
            res = conn.execute(text("""
                DELETE FROM policy_rules
                WHERE policy_id IN (
                    SELECT id FROM policies WHERE org_id NOT IN :org_ids
                )
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["policy_rules"] = res.rowcount

            # 5. Policies
            res = conn.execute(text("""
                DELETE FROM policies WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["policies"] = res.rowcount

            # 6. Agent executions
            res = conn.execute(text("""
                DELETE FROM agent_executions WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["agent_executions"] = res.rowcount

            # 7. Approval requests
            res = conn.execute(text("""
                DELETE FROM approval_requests
                WHERE agent_id IN (
                    SELECT id FROM agents WHERE org_id NOT IN :org_ids
                )
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["approval_requests"] = res.rowcount

            # 8. Provenance events
            res = conn.execute(text("""
                DELETE FROM provenance_events
                WHERE agent_id IN (
                    SELECT id FROM agents WHERE org_id NOT IN :org_ids
                )
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["provenance_events"] = res.rowcount

            # 9. Decisions
            res = conn.execute(text("""
                DELETE FROM decisions
                WHERE agent_id IN (
                    SELECT id FROM agents WHERE org_id NOT IN :org_ids
                )
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["decisions"] = res.rowcount

            # 10. Agent children
            agent_children = [
                'agent_credentials', 'agent_passports', 'agent_runtime_sessions',
                'capability_tokens', 'circuit_breakers', 'behavior_profiles',
                'budgets', 'permissions', 'reputation_scores', 'security_tests',
                'simulations', 'anomaly_events', 'runtime_risk_signals'
            ]
            for child in agent_children:
                res = conn.execute(text(f"""
                    DELETE FROM "{child}"
                    WHERE agent_id IN (
                        SELECT id FROM agents WHERE org_id NOT IN :org_ids
                    )
                """), {"org_ids": GENUINE_ORG_IDS})
                stats[child] = res.rowcount

            # 11. Security incidents
            res = conn.execute(text("""
                DELETE FROM security_incidents WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["security_incidents"] = res.rowcount

            # 12. Scheduled reports & report histories
            res = conn.execute(text("""
                DELETE FROM scheduled_reports WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["scheduled_reports"] = res.rowcount

            res = conn.execute(text("""
                DELETE FROM report_histories WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["report_histories"] = res.rowcount

            # 13. Api keys
            res = conn.execute(text("""
                DELETE FROM api_keys WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["api_keys"] = res.rowcount

            # 14. Tools
            res = conn.execute(text("""
                DELETE FROM tools WHERE org_id NOT IN :org_ids_str
            """), {"org_ids_str": tuple(GENUINE_ORG_IDS)})
            stats["tools"] = res.rowcount

            # 15. User invitations
            res = conn.execute(text("""
                DELETE FROM user_invitations WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["user_invitations"] = res.rowcount

            # 16. Notifications & sessions
            res = conn.execute(text("""
                DELETE FROM notifications
                WHERE user_id NOT IN (
                    SELECT id FROM users WHERE email IN :emails
                )
            """), {"emails": GENUINE_USER_EMAILS})
            stats["notifications"] = res.rowcount

            res = conn.execute(text("""
                DELETE FROM sessions
                WHERE user_id NOT IN (
                    SELECT id FROM users WHERE email IN :emails
                )
            """), {"emails": GENUINE_USER_EMAILS})
            stats["sessions"] = res.rowcount

            # 17. License usages & licenses
            res = conn.execute(text("""
                DELETE FROM license_usages WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["license_usages"] = res.rowcount

            res = conn.execute(text("""
                DELETE FROM licenses WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["licenses"] = res.rowcount

            # 18. Agents
            res = conn.execute(text("""
                DELETE FROM agents WHERE org_id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["agents"] = res.rowcount

            # 19. Users
            res = conn.execute(text("""
                DELETE FROM users WHERE email NOT IN :emails
            """), {"emails": GENUINE_USER_EMAILS})
            stats["users"] = res.rowcount

            # 20. Organizations
            res = conn.execute(text("""
                DELETE FROM organizations WHERE id NOT IN :org_ids
            """), {"org_ids": GENUINE_ORG_IDS})
            stats["organizations"] = res.rowcount

            trans.commit()
            print("[SUCCESS] Transaction committed successfully to database!")

        except Exception as e:
            trans.rollback()
            print(f"[FAIL] Cleanup transaction failed and was rolled back: {e}")
            raise e

    print("\n--- CLEANUP SUMMARY REPORT ---")
    total_deleted = sum(v for k, v in stats.items() if not k.endswith("_disassociated"))
    print(f"Total dummy/demo/test records deleted: {total_deleted}")
    for k, v in sorted(stats.items()):
        print(f"  * {k}: {v}")

    return stats

if __name__ == "__main__":
    execute_cleanup()
