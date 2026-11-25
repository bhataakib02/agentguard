import os
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:postgres@localhost:5435/postgres"
engine = create_engine(db_url)

rollback_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql"))
with open(rollback_path, "r", encoding="utf-8") as f:
    sql = f.read()

print("Applying rollback SQL...")
with engine.connect() as conn:
    with conn.begin():
        conn.execute(text(sql))

# Verify policies count
with engine.connect() as conn:
    policy_count = conn.execute(text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public';")).scalar()
    rls_enabled_count = conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true;")).scalar()
    print(f"Remaining policies after rollback: {policy_count}")
    print(f"Remaining RLS-enabled tables after rollback: {rls_enabled_count}")

if policy_count == 0 and rls_enabled_count == 0:
    print("ROLLBACK VERIFIED: All policies cleanly dropped and RLS disabled on all tables!")
else:
    raise RuntimeError(f"Rollback incomplete: {policy_count} policies, {rls_enabled_count} RLS tables remain.")
