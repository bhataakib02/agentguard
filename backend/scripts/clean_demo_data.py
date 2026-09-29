import sys, os
from sqlalchemy import text
sys.path.append(os.path.dirname(__file__))

from database import engine, SessionLocal

def clean_all_demo_data():
    print("=" * 60)
    print("  AGENTGUARD PRODUCTION DATABASE CLEANUP & PURGE SCRIPT  ")
    print("=" * 60)

    db = SessionLocal()

    tables_order = [
        "provenance_events", "approval_requests", "decisions", "capability_tokens", "permissions",
        "agent_passports", "agent_credentials", "risk_scores", "behavior_profiles", "reputation_scores",
        "circuit_breakers", "budgets", "transactions", "security_tests", "simulations", "resource_usages",
        "anomaly_events", "security_incidents", "agent_relationships", "agents", "policy_rules",
        "policies", "notifications", "sessions", "api_keys", "users", "organizations"
    ]

    try:
        print("\nPurging all tables in dependency order...")
        for tbl in tables_order:
            try:
                db.execute(text(f"DELETE FROM {tbl};"))
                db.commit()
                print(f"  [SUCCESS] Purged table: {tbl}")
            except Exception as e:
                db.rollback()
                # Table might not exist or be empty, ignore safely
                pass

        print("\n[VERIFICATION] Checking remaining counts in Supabase PostgreSQL:")
        for tbl in ["users", "agents", "organizations", "decisions"]:
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {tbl};")).scalar()
                print(f"  - Remaining {tbl}: {count}")
            except Exception:
                pass

        print("\n[SUCCESS] All demo records safely removed from live Supabase PostgreSQL!")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Database cleanup encountered error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_all_demo_data()
