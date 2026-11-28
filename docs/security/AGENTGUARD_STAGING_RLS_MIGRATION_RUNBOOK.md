# AGENTGUARD — Staging Database RLS Migration & Hardening Runbook

**Document Reference**: AGENTGUARD-RLS-RUNBOOK-2026-11-28  
**Target Environment**: Dedicated Staging PostgreSQL 15+ / Supabase Staging Project  
**Authoritative Migration**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql`  
**Authoritative Rollback**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql`  
**Execution Status**: **PREPARED — READY FOR AUTHORIZED STAGING EXECUTION**  
*(Strictly forbidden to run against production database `xjragvyzlailmtfwjfnm`)*

---

## 1. Overview & Operational Principles

This runbook defines the exact, step-by-step procedure for executing and verifying PostgreSQL Row Level Security (RLS) policies and PostgREST role privilege hardening on the dedicated **AGENTGUARD Staging Database**.

### Core Operational Principles:
- **Transaction Safety**: All DDL commands in the migration script are wrapped in an explicit `BEGIN ... COMMIT;` block. Any syntax error, constraint conflict, or permission failure immediately triggers an automatic transaction abort, preventing partial or corrupt policy states.
- **Idempotency**: All policies are created with `DROP POLICY IF EXISTS ...; CREATE POLICY ...;`. The migration can be executed repeatedly without failing or duplicating rules.
- **Dual-Layer Defense**: Application-layer `org_id` filtering in SQLAlchemy remains the primary isolation layer; database-layer RLS acts as an independent defense-in-depth shield against direct PostgREST exposure, accidental query omission, or SQL injection.
- **Backend Continuity**: The migration explicitly grants `service_role_all` on all tables to role `service_role` and preserves `rolbypassrls = true` for `postgres`, ensuring zero disruption to FastAPI background tasks, Celery workers, and connection pools.

---

## 2. Table & Policy Architecture Matrix

The migration governs all **50 tables** in the AGENTGUARD database across 5 architectural tiers:

| Tier | Table Type / Description | Table List | RLS Policy Applied | PostgREST Client Access |
|---|---|---|---|---|
| **Tier 1** | Direct Tenant Boundary | `organizations` | `tenant_isolation_organizations`: `id = current_org_id() OR is_super_admin()` | Scoped to caller tenant. |
| **Tier 2** | Direct Tenant-Bearing Tables (`org_id NOT NULL`) | `agents`, `users`, `api_keys`, `policies`, `webhook_endpoints`, `scheduled_reports`, `report_histories`, `security_incidents`, `runtime_risk_signals`, `sandbox_execution_jobs`, `agent_budget_configs`, `agent_executions`, `evaluation_datasets`, `evaluation_dataset_records`, `evaluation_scenarios`, `evaluation_scenario_records`, `siem_deliveries`, `user_invitations`, `licenses`, `license_usages`, `guardrail_rules`, `integration_configs`, `network_policies`, `optimization_rules` | `tenant_isolation`: `org_id = current_org_id() OR is_super_admin()` | Scoped CRUD to caller tenant. |
| **Tier 3** | Parent-Child Indirect Tenant Tables | `agent_credentials`, `agent_passports`, `agent_runtime_sessions`, `anomaly_events`, `approval_requests`, `behavior_profiles`, `budgets`, `capability_tokens`, `circuit_breakers`, `permissions`, `provenance_events`, `reputation_scores`, `resource_usages`, `risk_scores`, `security_tests`, `simulations`, `transactions`, `webhook_deliveries`, `policy_rules` | Parent join check: `EXISTS (SELECT 1 FROM agents/webhooks/policies WHERE parent.id = child.parent_id AND parent.org_id = current_org_id())` | Scoped to parent tenant. |
| **Tier 4** | Specialized Polymorphic & Dual-Agent Tables | `decisions` (dual polymorphic validation: agent in tenant AND/OR user in tenant), `agent_relationships` (validates BOTH `parent_agent_id` AND `child_agent_id` belong to caller tenant), `notifications` (scoped per-user: `users.auth_user_id = auth.uid() AND users.org_id = current_org_id()`) | Specialized dual-check subquery policies | Strict multi-entity ownership validation. |
| **Tier 5** | Locked Down & Global Reference Tables | `audit_logs` (read-only for authenticated, zero UPDATE/DELETE policies), `tools` / `siem_configs` (read global + tenant; modify tenant only), `plans`, `ai_models`, `capabilities`, `model_pricing` (read-only catalog; super-admin write), `sessions`, `otp_challenges` (PostgREST completely revoked; backend service_role only) | Table-level privilege revocation + targeted policies | Zero client access to sessions/OTPs; immutable audit trail. |

---

## 3. Step-by-Step Staging Execution Runbook

Follow these 19 steps in exact chronological sequence when authorized to execute the staging migration:

### Step 1: Confirm Staging Database Identity
Verify that your active shell environment variables point strictly to the dedicated staging database and **NOT** to production:
```bash
# Verify connection string does NOT contain production project reference (xjragvyzlailmtfwjfnm)
if [[ "$STAGING_DATABASE_URL" == *"xjragvyzlailmtfwjfnm"* ]]; then
    echo "FATAL: STAGING_DATABASE_URL points to PRODUCTION! Aborting immediately."
    exit 1
fi
echo "Target Verified: STAGING database confirmed."
```

### Step 2: Verify Staging Connection
Test basic database connectivity and latency:
```bash
psql "$STAGING_DATABASE_URL" -c "SELECT current_database(), current_user, inet_server_addr();"
```

### Step 3: Verify Database Backups
Ensure point-in-time recovery (PITR) is active on Supabase staging, or create an explicit pre-migration logical snapshot:
```bash
pg_dump "$STAGING_DATABASE_URL" -Fc -f "staging_pre_rls_$(date +%Y%m%d_%H%M%S).dump"
ls -lh staging_pre_rls_*.dump
```

### Step 4: Verify PostgreSQL Version
Ensure staging is running PostgreSQL 15 or 17 (matching production engine):
```bash
psql "$STAGING_DATABASE_URL" -t -c "SHOW server_version;"
```

### Step 5: Verify Current Baseline Schema
Confirm that Alembic has created all 50 application tables and stamped baseline revision `0002_add_otp_challenges`:
```bash
psql "$STAGING_DATABASE_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
# Expected: >= 50
psql "$STAGING_DATABASE_URL" -c "SELECT version_num FROM alembic_version;"
# Expected: 0002_add_otp_challenges_table
```

### Step 6: Review Migration Script Integrity
Inspect the SHA-256 checksum of the migration file to ensure no unauthorized modifications occurred:
```bash
sha256sum docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql
sha256sum docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql
```

### Step 7: Verify Migration Preconditions
Ensure required PostgreSQL extensions are active in staging:
```bash
psql "$STAGING_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
```

### Step 8: Apply Migration (Execute Transaction)
*Only execute after receiving explicit authorization.*
```bash
psql "$STAGING_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql
```
*If any error occurs, psql halts immediately with non-zero exit code and the entire script rolls back cleanly.*

### Step 9: Verify Policy Inventory
Verify that all 50 tables have RLS enabled and policies are populated:
```bash
psql "$STAGING_DATABASE_URL" -c "
SELECT count(*) AS rls_enabled_tables 
FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = true;
"
# Expected: 50

psql "$STAGING_DATABASE_URL" -c "
SELECT schemaname, tablename, count(policyname) AS policy_count 
FROM pg_policies 
WHERE schemaname = 'public' 
GROUP BY schemaname, tablename 
ORDER BY tablename;
"
```

### Step 10: Run Automated RLS Integration Tests
Execute the dedicated PostgreSQL RLS integration test suite against the staging database:
```bash
export POSTGRES_TEST_URL="$STAGING_DATABASE_URL"
python -m pytest backend/tests/test_postgresql_rls_validation.py -v --tb=short
# Expected: 15 passed, 0 failed, 0 errors
```

### Step 11: Verify Tenant Isolation Invariant (Tenant A vs Tenant B)
Execute manual verification query simulating authenticated PostgREST roles:
```sql
-- Simulate Tenant A session via SET LOCAL
BEGIN;
SET LOCAL ROLE authenticated;
SET LOCAL request.jwt.claims = '{"app_metadata": {"org_id": "00000000-0000-0000-0000-000000000001"}}';

-- Query records belonging to Tenant B (must return 0)
SELECT count(*) FROM public.agents WHERE org_id = '00000000-0000-0000-0000-000000000002';
-- Expected: 0

-- Attempt to update Tenant B agent (must affect 0 rows)
UPDATE public.agents SET name = 'tampered' WHERE org_id = '00000000-0000-0000-0000-000000000002';
-- Expected: UPDATE 0
ROLLBACK;
```

### Step 12: Verify Role & Privilege Hardening Behavior
Confirm that dangerous privileges have been revoked from client roles:
```sql
SELECT 
    has_table_privilege('anon', 'public.users', 'TRUNCATE') AS anon_truncate,
    has_table_privilege('authenticated', 'public.users', 'TRUNCATE') AS auth_truncate,
    has_table_privilege('anon', 'public.users', 'REFERENCES') AS anon_ref,
    has_table_privilege('authenticated', 'public.users', 'REFERENCES') AS auth_ref,
    has_table_privilege('service_role', 'public.users', 'ALL') AS service_all;
-- Expected: anon_truncate = false, auth_truncate = false, anon_ref = false, auth_ref = false, service_all = true
```

### Step 13: Verify GUC Spoofing Resistance
Verify that arbitrary user-set GUCs cannot spoof super-admin or tenant identity:
```sql
BEGIN;
SET LOCAL ROLE authenticated;
-- Attacker attempts to spoof GUC directly
SET LOCAL app.is_super_admin = 'true';
SET LOCAL app.current_org_id = '00000000-0000-0000-0000-000000000002';

-- Helper function must reject unverified GUC for authenticated role!
SELECT public.is_super_admin(); -- Must return FALSE
SELECT public.current_org_id(); -- Must return NULL (no valid request.jwt.claims)
ROLLBACK;
```

### Step 14: Verify Connection Pool Context Isolation
Verify that `SET LOCAL` settings do not leak across pooled connections:
```sql
-- Session 1 sets tenant context inside transaction
BEGIN;
SET LOCAL app.current_org_id = '00000000-0000-0000-0000-000000000001';
COMMIT;

-- Session 2 executes outside transaction; must evaluate to NULL
SELECT nullif(current_setting('app.current_org_id', true), '');
-- Expected: NULL (zero leakage across pooled connections)
```

### Step 15: Verify Global Reference Table Behavior
Verify that all authenticated tenants can SELECT global tools (`org_id IS NULL`), but cannot update or delete them:
```sql
BEGIN;
SET LOCAL ROLE authenticated;
SET LOCAL request.jwt.claims = '{"app_metadata": {"org_id": "00000000-0000-0000-0000-000000000001"}}';

-- Read global tool (must succeed)
SELECT count(*) FROM public.tools WHERE org_id IS NULL; -- >= 0

-- Attempt to delete global tool (must affect 0 rows)
DELETE FROM public.tools WHERE org_id IS NULL; -- DELETE 0
ROLLBACK;
```

### Step 16: Verify Audit Log Immutability
Verify that authenticated users can INSERT and SELECT audit logs, but cannot UPDATE or DELETE:
```sql
BEGIN;
SET LOCAL ROLE authenticated;
SET LOCAL request.jwt.claims = '{"app_metadata": {"org_id": "00000000-0000-0000-0000-000000000001"}}';

-- UPDATE must fail with permission denied error
UPDATE public.audit_logs SET result = 'TAMPERED';
-- Expected: ERROR: permission denied for table audit_logs
ROLLBACK;
```

### Step 17: Verify Session and OTP Table Protection
Verify that client PostgREST roles (`anon`, `authenticated`) have zero access to raw session tokens and OTP challenge records:
```sql
BEGIN;
SET LOCAL ROLE authenticated;
SELECT count(*) FROM public.sessions;
-- Expected: ERROR: permission denied for table sessions
ROLLBACK;

BEGIN;
SET LOCAL ROLE authenticated;
SELECT count(*) FROM public.otp_challenges;
-- Expected: ERROR: permission denied for table otp_challenges
ROLLBACK;
```

### Step 18: Reversibility & Rollback Drill (Dry Run)
Verify that the companion rollback script cleanly disables RLS and removes all policies without corrupting table data:
```bash
# 1. Run rollback script
psql "$STAGING_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql

# 2. Verify all policies dropped and RLS disabled
psql "$STAGING_DATABASE_URL" -c "SELECT count(*) FROM pg_policies WHERE schemaname = 'public';"
# Expected: 0
psql "$STAGING_DATABASE_URL" -c "SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true;"
# Expected: 0

# 3. Re-apply forward migration to leave staging hardened
psql "$STAGING_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql
```

### Step 19: Document Execution Results
Record the migration date, staging project reference, test run output, and operator signature in `docs/security/POSTGRESQL_VALIDATION_REPORT.md`.

---

## 4. Emergency Troubleshooting & Rollback Matrix

| Symptom / Failure Mode | Root Cause | Immediate Action |
|---|---|---|
| Backend returns `500 Internal Server Error` on entity queries | SQLAlchemy connection pool is not passing `service_role` credentials or `BYPASSRLS` is disabled. | Verify `DATABASE_URL` connects as `postgres` or `service_role`. Re-execute `GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;`. |
| PostgREST returns 0 rows for valid tenant user | User JWT token missing `app_metadata.org_id` claim, causing `current_org_id()` to return NULL. | Inspect JWT payload in client. Verify user profile has `org_id` populated; helper function will fallback to database profile lookup. |
| Migration aborts with `ERROR: relation "..." does not exist` | Alembic baseline has not been applied to staging database before executing RLS migration. | Run `alembic upgrade head` first to create all 50 tables, then re-execute RLS script. |
| Catastrophic application failure / widespread query degradation | Unanticipated RLS policy conflict with third-party service. | Execute immediate rollback: `psql "$STAGING_DATABASE_URL" -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql`. Application-layer security remains active. |
