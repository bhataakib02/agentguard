# AGENTGUARD Database Defense-in-Depth RLS Migration Runbook

## 1. Overview & Change Management Protocol

This operational runbook governs the deployment of PostgreSQL Row Level Security (RLS) policies and PostgREST privilege hardening for AGENTGUARD. 

- **Migration File**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql`
- **Rollback File**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql`
- **Current Operational Status**: **GATED / MIGRATION BLOCKED** pending correction of the 6 identified SQL security defects and local PostgreSQL validation.
- **Risk Classification**: Medium-High (Requires transaction-wrapped deployment, TRUNCATE privilege revocation, and application verification).
- **Deployment Window**: Standard maintenance or zero-downtime rolling update (policies include full `service_role` bypass, ensuring backend continuity).

---

## 2. Pre-Flight Verification Checklist

Before executing the migration in staging or production:

- [ ] **SQL Defects Remediated**: Confirm that `audit_logs` is read-only, `tools` permits `org_id IS NULL`, `agent_relationships` validates both agents, `sessions` is service_role only, and `decisions` has symmetric `WITH CHECK`.
- [ ] **Local PostgreSQL Validation Passed**: Run `test_postgresql_rls_validation.py` against a disposable local PostgreSQL container.
- [ ] **Database Backup**: Verify that an automated point-in-time recovery (PITR) snapshot or physical `pg_dump` backup completed within the last 60 minutes.
- [ ] **Alembic Version Alignment**: Confirm Alembic has adopted the baseline and stamped `0002_add_otp_challenges`.
- [ ] **Connection Pooling Check**: Verify backend session manager uses transaction-scoped `SET LOCAL app.current_org_id = ...`.
- [ ] **Application Test Suite Green**: Backend regression suite verified at 737/737 passed.

---

## 3. Phased Deployment Procedure

### Phase 1: Staging Dry-Run
```bash
# 1. Connect to Staging Database via psql as postgres administrator
psql "$STAGING_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql

# 2. Verify all policies are created
psql "$STAGING_DATABASE_URL" -c "SELECT tablename, policyname, permissive, roles, cmd FROM pg_policies WHERE schemaname = 'public' ORDER BY tablename;"

# 3. Verify TRUNCATE revocation on anon and authenticated
psql "$STAGING_DATABASE_URL" -c "SELECT has_table_privilege('anon', 'public.users', 'TRUNCATE') AS anon_truncate, has_table_privilege('authenticated', 'public.users', 'TRUNCATE') AS auth_truncate;"
# Must return FALSE for both!

# 4. Verify backend health
curl -I https://staging-api.agentguard.io/api/health
```

### Phase 2: Production Execution Protocol
1. Announce start of migration window on engineering status channel.
2. Execute migration script inside a transaction:
   ```bash
   psql "$PROD_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql
   ```
   *Note: Because the entire migration script is wrapped in `BEGIN ... COMMIT;`, any error will automatically trigger an immediate rollback, preventing partial policy states.*

3. Execute Post-Migration Verification Queries:
   ```sql
   -- 1. Ensure RLS is active on all 50 public tables
   SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true;
   -- Expected: 50

   -- 2. Validate helper functions fail closed
   SELECT public.current_org_id(); -- Must return NULL
   SELECT public.is_super_admin();  -- Must return FALSE

   -- 3. Verify anon has NO SELECT or TRUNCATE on users
   SELECT has_table_privilege('anon', 'public.users', 'SELECT');   -- FALSE
   SELECT has_table_privilege('anon', 'public.users', 'TRUNCATE'); -- FALSE

   -- 4. Verify authenticated has NO TRUNCATE
   SELECT has_table_privilege('authenticated', 'public.users', 'TRUNCATE'); -- FALSE

   -- 5. Verify service_role retains full access
   SELECT has_table_privilege('service_role', 'public.users', 'ALL'); -- TRUE
   ```

4. Execute API Smoke Tests:
   - User Login and JWT issuance.
   - Query `/api/agents` as Org Admin A (only Org A visible).
   - Query `/api/decisions` as Org Admin B (only Org B visible).
   - Test capability token validation via `/api/capabilities/validate`.
   - Verify immutable audit log rejection on attempted update.

---

## 4. Emergency Rollback Procedure

If the migration causes unexpected query failures, connection pool lockouts, or ORM degradation:

```bash
# Execute the automated rollback script
psql "$PROD_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls_rollback.sql
```

### What the Rollback Script Executes:
1. Drops all RLS policies in the `public` schema.
2. Disables Row Level Security (`ALTER TABLE ... DISABLE ROW LEVEL SECURITY`) on all public tables.
3. Drops helper functions `public.current_org_id()` and `public.is_super_admin()`.
4. Leaves application-layer security intact and operational.
