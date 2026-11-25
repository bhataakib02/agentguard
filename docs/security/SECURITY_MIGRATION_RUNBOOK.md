# AGENTGUARD Database Defense-in-Depth RLS Migration Runbook

## 1. Overview & Change Management Protocol

This operational runbook governs the deployment of PostgreSQL Row Level Security (RLS) policies and PostgREST privilege hardening for AGENTGUARD. 

- **Migration File**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql`
- **Rollback File**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql`
- **Risk Classification**: Medium (Requires transaction-wrapped deployment and application verification)
- **Deployment Window**: Standard maintenance or zero-downtime rolling update (policies include full `service_role` bypass, ensuring backend continuity).

---

## 2. Pre-Flight Verification Checklist

Before executing the migration in staging or production:

- [ ] **Database Backup**: Verify that an automated point-in-time recovery (PITR) snapshot or physical `pg_dump` backup completed within the last 60 minutes.
- [ ] **Role Existence**: Ensure `anon`, `authenticated`, and `service_role` exist in the target PostgreSQL instance (standard on Supabase).
- [ ] **Alembic Version**: Confirm Alembic is at `0002_add_otp_challenges` (`alembic current`).
- [ ] **Connection Pooling Check**: Verify that backend database session managers use transaction scoping (`SET LOCAL app.current_org_id = ...`) to prevent context bleed across pooled connections.
- [ ] **Test Suite Green**: Full backend regression test suite must be 100% passing (737/737 tests).

---

## 3. Staging Deployment & Dry Run

Execute the migration against the staging database first:

```bash
# 1. Connect to Staging Database via psql as superuser / postgres
psql "$STAGING_DATABASE_URL" -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql

# 2. Verify all policies are created
psql "$STAGING_DATABASE_URL" -c "SELECT tablename, policyname, permissive, roles, cmd FROM pg_policies WHERE schemaname = 'public';"

# 3. Verify backend connectivity
curl -I https://staging-api.agentguard.io/api/health
```

---

## 4. Production Execution Procedure

### Step 1: Notify Operational Team & Begin Maintenance Window
Announce the start of migration window on the engineering status channel.

### Step 2: Execute Migration Script
Run the transaction-wrapped migration using the `postgres` administrative role:
```bash
psql "$PROD_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql
```
*Note: Because the entire migration script is wrapped in `BEGIN ... COMMIT;`, any error will automatically trigger an immediate rollback, preventing partial policy states.*

### Step 3: Run Post-Migration Verification Queries
Execute the following verification queries immediately:
```sql
-- 1. Ensure RLS is active on all public tenant tables
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- 2. Validate helper functions
SELECT public.current_org_id(); -- Must return NULL
SELECT public.is_super_admin();  -- Must return FALSE

-- 3. Verify anon has no SELECT on users or organizations
SELECT has_table_privilege('anon', 'public.users', 'SELECT'); -- Must return FALSE
SELECT has_table_privilege('anon', 'public.organizations', 'SELECT'); -- Must return FALSE

-- 4. Verify service_role retains full access
SELECT has_table_privilege('service_role', 'public.users', 'SELECT'); -- Must return TRUE
SELECT has_table_privilege('service_role', 'public.organizations', 'ALL'); -- Must return TRUE
```

### Step 4: Execute API Smoke Tests
1. Test User Login and JWT issuance.
2. Query `/api/decisions` as Organization Admin A. Verify only Org A decisions appear.
3. Query `/api/agents` as Organization Admin B. Verify only Org B agents appear.
4. Execute `/api/capabilities/validate` with an active capability token.
5. Trigger a test notification and scheduled report.

---

## 5. Emergency Rollback Procedure

If the migration causes unexpected query failures, connection pool lockouts, or ORM degradation:

```bash
# Execute the automated rollback script
psql "$PROD_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql
```

The rollback script:
1. Drops all RLS policies in the `public` schema.
2. Disables Row Level Security (`ALTER TABLE ... DISABLE ROW LEVEL SECURITY`) on all tables.
3. Drops `public.current_org_id()` and `public.is_super_admin()`.
4. Leaves application-layer security intact and operational.
