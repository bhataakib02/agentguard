# AGENTGUARD — Row Level Security (RLS) Production Readiness Audit

**Document Version**: 2.0.0 (Remediated)  
**Target Migration**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql`  
**Classification**: **RLS DESIGN CORRECTED — POSTGRESQL VALIDATION PENDING**  

---

## 1. Executive Summary

Following the initial audit that blocked deployment due to 6 critical design flaws, the proposed Row Level Security architecture and migration scripts have been completely redesigned and remediated.

All 6 identified security defects have been corrected in `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql`:
1. **Immutable Audit Logs**: `audit_logs` is restricted to `FOR SELECT` and `FOR INSERT` only. Zero `UPDATE` or `DELETE` permissions exist for `authenticated`.
2. **Global Platform Tools**: `tools` allows `SELECT` on `org_id IS NULL OR org_id = current_org_id()`, preserving global tool visibility while barring tenant mutation.
3. **Dual-Agent Relational Integrity**: `agent_relationships` validates that **both** `parent_agent_id` AND `child_agent_id` belong to `current_org_id()`, preventing cross-tenant bridging.
4. **Session Token Lockdown**: `sessions` is revoked entirely from `anon` and `authenticated`, eliminating intra-tenant token theft.
5. **Symmetric Decision Checks**: `decisions` harmonizes `USING` and `WITH CHECK` to symmetrically validate human decisions, agent decisions, and reject cross-tenant mismatches.
6. **Anti-GUC Spoofing & PostgREST Identity**: Helper functions `public.current_org_id()` and `public.is_super_admin()` ignore custom `app.*` GUCs when executing as `authenticated` or `anon`, resolving tenant identity strictly from verified JWT claims or authoritative database profiles.

**Next Milestone**: Execution of the 15-test PostgreSQL integration suite against a disposable local PostgreSQL container once Docker Desktop is started.

---

## 2. Remediated SQL Architecture Verification

| Defect # | Component | Original Vulnerability | Remediated Design | Verification Status |
|---|---|---|---|---|
| 1 | `audit_logs` | `FOR ALL` policy allowed tenant `UPDATE` / `DELETE` | Separated into `tenant_read_audit_logs` (SELECT) and `tenant_insert_audit_logs` (INSERT). No UPDATE/DELETE policy created. | **REMEDIATED** |
| 2 | `tools` | `org_id = current_org_id()` hid global tools (`org_id IS NULL`) | `tenant_read_tools` includes `OR org_id IS NULL`. Writes restricted to tenant-owned tools. | **REMEDIATED** |
| 3 | `agent_relationships` | Checked only `parent_agent_id`, allowing cross-tenant child linking | Policy enforces `EXISTS (parent_agent IN tenant) AND EXISTS (child_agent IN tenant)`. | **REMEDIATED** |
| 4 | `sessions` | Tenant peers could select colleague JWT/refresh tokens | Revoked all direct access (`REVOKE ALL ON sessions FROM anon, authenticated`). Service role exclusive. | **REMEDIATED** |
| 5 | `decisions` | Asymmetric `WITH CHECK` blocked human decisions; allowed mismatch | Symmetrically checks human and agent decisions; enforces single-tenant alignment when both are populated. | **REMEDIATED** |
| 6 | GUC Spoofing | Untrusted users could run `SET app.is_super_admin = 'true'` | `current_org_id()` and `is_super_admin()` evaluate GUCs only if `CURRENT_USER IN ('postgres', 'service_role')`. PostgREST uses verified JWT / DB profile. | **REMEDIATED** |

---

## 3. Privilege Hardening Specification

The forward migration script incorporates explicit permission hardening to eliminate inherited and default `TRUNCATE` privileges:

```sql
-- 1. Strip all privileges from unauthenticated web clients
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- 2. Strip dangerous TRUNCATE, REFERENCES, TRIGGER from authenticated clients
REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM authenticated;

-- 3. Grant scoped CRUD to authenticated (strictly governed by RLS)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- 4. Explicitly revoke write access on immutable / sensitive tables
REVOKE UPDATE, DELETE ON public.audit_logs FROM authenticated;
REVOKE ALL ON public.sessions FROM anon, authenticated;
REVOKE ALL ON public.otp_challenges FROM anon, authenticated;

-- 5. Fix default privileges for future tables created under postgres
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;
```

---

## 4. Deployment Gating & Conditions for Sign-Off

The migration is gated and must not be applied to staging or production until:
1. **Docker Engine Available**: Launch Docker Desktop on Windows workstation.
2. **Local PostgreSQL Suite Green**: Run `pytest backend/tests/test_postgresql_rls_validation.py` against disposable container with 15/15 tests passing.
3. **Idempotency Verified**: Confirm re-running the migration script against the container executes with 0 errors.
4. **Rollback Verified**: Confirm executing the rollback script restores application-layer-only access cleanly.
