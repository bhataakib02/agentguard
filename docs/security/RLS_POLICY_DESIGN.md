# AGENTGUARD PostgreSQL RLS Policy Design & Implementation Specification

## 1. Context & Architectural Critique of Previous Proposed RLS Migration

In the preliminary security audit, a proposed migration (`20261125000000_defense_in_depth_rls_remediation.sql`) was drafted. Independent review determined that executing that script in production would cause severe backend outages:

1. **Premature `FORCE ROW LEVEL SECURITY`**:
   - The script forced RLS on 33 tables. Under PostgreSQL semantics, `FORCE ROW LEVEL SECURITY` forces table owners (including the backend connection user when connecting as table owner) to be constrained by policies.
   - However, backend bypass policies were only provided for 4 tables (`organizations`, `users`, `agents`, `decisions`).
   - The remaining 29 tables had **zero** policies for the backend role, causing queries on those tables to return 0 rows or throw access violations immediately.
2. **Non-Idempotent DDL**:
   - The script executed raw `CREATE POLICY` statements without `DROP POLICY IF EXISTS`. Re-running or retrying after a partial failure caused `duplicate policy` errors.
3. **Session Context Bleed**:
   - The script relied on session-level `SET app.current_org_id`, which fails in pooled connection environments (PgBouncer/SQLAlchemy QueuePool).
4. **Missing Parent-Child Policies**:
   - Tables lacking `org_id` were either ignored or had invalid column references.

The redesigned migration (`20261125010000_idempotent_defense_in_depth_rls.sql`) remedies all of these defects.

---

## 2. Policy Archetypes & SQL Expressions

### Archetype A: Direct Tenant-Bearing Tables
Tables that feature an explicit `org_id uuid NOT NULL` column (e.g. `agents`, `users`, `policies`, `tools`, `audit_logs`).

```sql
-- Pattern for Direct Tenant Tables
ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;

-- 1. Service Role (Backend & Celery) Bypass
DROP POLICY IF EXISTS service_role_all ON public.<table_name>;
CREATE POLICY service_role_all ON public.<table_name>
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- 2. Authenticated Tenant Isolation Policy
DROP POLICY IF EXISTS tenant_isolation ON public.<table_name>;
CREATE POLICY tenant_isolation ON public.<table_name>
    FOR ALL TO authenticated
    USING (org_id = public.current_org_id() OR public.is_super_admin())
    WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());
```

### Archetype B: Parent-Child Dependent Tables
Tables that inherit organization ownership through a foreign key to `agents.id`, `users.id`, or `webhook_endpoints.id` (e.g. `decisions`, `capability_tokens`, `sessions`, `simulations`).

```sql
-- Pattern for Agent Children (e.g. capability_tokens, simulations)
ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.<table_name>;
CREATE POLICY service_role_all ON public.<table_name>
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS tenant_isolation ON public.<table_name>;
CREATE POLICY tenant_isolation ON public.<table_name>
    FOR ALL TO authenticated
    USING (
        public.is_super_admin()
        OR EXISTS (
            SELECT 1 FROM public.agents
            WHERE public.agents.id = public.<table_name>.agent_id
              AND public.agents.org_id = public.current_org_id()
        )
    )
    WITH CHECK (
        public.is_super_admin()
        OR EXISTS (
            SELECT 1 FROM public.agents
            WHERE public.agents.id = public.<table_name>.agent_id
              AND public.agents.org_id = public.current_org_id()
        )
    );
```

### Archetype C: Decisions Polymorphic Tenant Resolution
The `decisions` table can be originated either by an autonomous `agent_id` or by a human `user_id`.

```sql
ALTER TABLE public.decisions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.decisions;
CREATE POLICY service_role_all ON public.decisions
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS tenant_isolation ON public.decisions;
CREATE POLICY tenant_isolation ON public.decisions
    FOR ALL TO authenticated
    USING (
        public.is_super_admin()
        OR EXISTS (
            SELECT 1 FROM public.agents
            WHERE public.agents.id = public.decisions.agent_id
              AND public.agents.org_id = public.current_org_id()
        )
        OR (
            public.decisions.user_id IS NOT NULL
            AND EXISTS (
                SELECT 1 FROM public.users
                WHERE public.users.id = public.decisions.user_id
                  AND public.users.org_id = public.current_org_id()
            )
        )
    )
    WITH CHECK (
        public.is_super_admin()
        OR EXISTS (
            SELECT 1 FROM public.agents
            WHERE public.agents.id = public.decisions.agent_id
              AND public.agents.org_id = public.current_org_id()
        )
    );
```

### Archetype D: Global System Catalogs (Read-Only to Authenticated)
Reference tables (`plans`, `ai_models`, `capabilities`, `model_pricing`) contain platform-wide metadata.

```sql
ALTER TABLE public.<catalog_table> ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.<catalog_table>;
CREATE POLICY service_role_all ON public.<catalog_table>
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS authenticated_read_only ON public.<catalog_table>;
CREATE POLICY authenticated_read_only ON public.<catalog_table>
    FOR SELECT TO authenticated
    USING (true);

DROP POLICY IF EXISTS super_admin_write ON public.<catalog_table>;
CREATE POLICY super_admin_write ON public.<catalog_table>
    FOR ALL TO authenticated
    USING (public.is_super_admin())
    WITH CHECK (public.is_super_admin());
```

---

## 3. Helper Functions Specification

```sql
-- Function: public.current_org_id()
-- Converts string setting to uuid safely; returns NULL if unset/blank.
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT nullif(current_setting('app.current_org_id', true), '')::uuid;
$$;

-- Function: public.is_super_admin()
-- Validates verified super admin flag in current transaction context.
CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(current_setting('app.is_super_admin', true) = 'true', false);
$$;
```

---

## 4. Grant Architecture & PostgREST Surface Reduction

```sql
-- 1. Strip anon privileges
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- 2. Grant scoped DML to authenticated (gated by RLS policies above)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- 3. Grant full application access to service_role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;

-- 4. Default privileges for future schema objects created by migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
```
