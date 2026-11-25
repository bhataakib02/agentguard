# AGENTGUARD PostgreSQL RLS Policy Design & Implementation Specification

## 1. Architectural Critique of Proposed RLS Migration

During the Phase 5 independent safety audit, script `20261125010000_idempotent_defense_in_depth_rls.sql` was evaluated against real PostgreSQL semantics and application invariants. The audit identified **6 blocking design flaws** that must be remediated prior to execution:

1. **Audit Logs Mutability (`audit_logs`)**:
   - The script defined `FOR ALL TO authenticated` on `audit_logs`.
   - Combined with `GRANT SELECT, INSERT, UPDATE, DELETE ... TO authenticated`, this allows authenticated users to execute `UPDATE` and `DELETE` on their tenant's audit trail, destroying non-repudiation and regulatory compliance.
2. **Global Platform Tools Hidden (`tools`)**:
   - `tools.org_id` is nullable. Global tools have `org_id = NULL`.
   - The expression `org_id = public.current_org_id()` evaluates to `UNKNOWN` (falsy) for `org_id IS NULL`, rendering all system-provided AI tools completely invisible to tenant users.
3. **Cross-Tenant Relationship Injection (`agent_relationships`)**:
   - The policy checked only `parent_agent_id` against `public.current_org_id()`, leaving `child_agent_id` unconstrained.
   - An authenticated user could inject a relation linking an internal agent to a foreign organization's agent.
4. **Intra-Tenant Session Token Bleed (`sessions`)**:
   - The policy allowed any authenticated user in an organization to select all `sessions` rows belonging to that organization.
   - Low-privileged users (e.g. `VIEWER`) could inspect and hijack active JWT and refresh tokens belonging to organization `ADMIN` users.
5. **Decisions `WITH CHECK` Asymmetry (`decisions`)**:
   - The `USING` clause supported human decisions via `user_id`, but the `WITH CHECK` clause strictly required `agent_id` to exist in `agents`.
   - Human-originated decisions failed on insertion, while cross-tenant mismatches between `agent_id` and `user_id` were not validated.
6. **Custom GUC Spoofing**:
   - Relying solely on `current_setting('app.is_super_admin', true)` allows any user with SQL execution privileges to execute `SET app.is_super_admin = 'true';` to disable RLS enforcement.

---

## 2. Hardened Policy Archetypes & SQL Specifications

### Archetype A: Direct Tenant-Bearing Tables
Tables that feature an explicit `org_id uuid NOT NULL` column (e.g. `agents`, `users`, `policies`, `siem_deliveries`).

```sql
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

### Archetype B: Immutable Audit Trail (`audit_logs`)
Audit logs must be append-only or write-only from the application, and read-only to tenant users.

```sql
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.audit_logs;
CREATE POLICY service_role_all ON public.audit_logs
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can SELECT only their own tenant's audit events
DROP POLICY IF EXISTS tenant_read_audit_logs ON public.audit_logs;
CREATE POLICY tenant_read_audit_logs ON public.audit_logs
    FOR SELECT TO authenticated
    USING (org_id = public.current_org_id() OR public.is_super_admin());

-- Authenticated users can INSERT only events matching their tenant
DROP POLICY IF EXISTS tenant_insert_audit_logs ON public.audit_logs;
CREATE POLICY tenant_insert_audit_logs ON public.audit_logs
    FOR INSERT TO authenticated
    WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());

-- CRITICAL: NO UPDATE or DELETE policies are created for authenticated!
-- Under PostgreSQL RLS, lack of an UPDATE/DELETE policy results in default-deny.
```

### Archetype C: Hybrid Global + Tenant Tables (`tools`, `siem_configs`)
Tables containing both global shared templates (`org_id IS NULL`) and tenant-customized entities.

```sql
ALTER TABLE public.tools ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.tools;
CREATE POLICY service_role_all ON public.tools
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Read: Allow access to tenant-owned tools AND global platform tools
DROP POLICY IF EXISTS tenant_tools_read ON public.tools;
CREATE POLICY tenant_tools_read ON public.tools
    FOR SELECT TO authenticated
    USING (org_id = public.current_org_id() OR org_id IS NULL OR public.is_super_admin());

-- Write: Tenant users can only insert/modify their own tenant-owned tools
DROP POLICY IF EXISTS tenant_tools_write ON public.tools;
CREATE POLICY tenant_tools_write ON public.tools
    FOR ALL TO authenticated
    USING (org_id = public.current_org_id() OR public.is_super_admin())
    WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());
```

### Archetype D: Dual-Agent Relational Integrity (`agent_relationships`)
Ensures that both endpoints of an agent delegation belong to the same tenant.

```sql
ALTER TABLE public.agent_relationships ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.agent_relationships;
CREATE POLICY service_role_all ON public.agent_relationships
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS tenant_isolation ON public.agent_relationships;
CREATE POLICY tenant_isolation ON public.agent_relationships
    FOR ALL TO authenticated
    USING (
        public.is_super_admin()
        OR (
            EXISTS (SELECT 1 FROM public.agents WHERE id = parent_agent_id AND org_id = public.current_org_id())
            AND EXISTS (SELECT 1 FROM public.agents WHERE id = child_agent_id AND org_id = public.current_org_id())
        )
    )
    WITH CHECK (
        public.is_super_admin()
        OR (
            EXISTS (SELECT 1 FROM public.agents WHERE id = parent_agent_id AND org_id = public.current_org_id())
            AND EXISTS (SELECT 1 FROM public.agents WHERE id = child_agent_id AND org_id = public.current_org_id())
        )
    );
```

### Archetype E: Session Security (`sessions`)
Prevents token harvesting within the same tenant.

```sql
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.sessions;
CREATE POLICY service_role_all ON public.sessions
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Revoke all direct PostgREST access from client roles
REVOKE ALL ON public.sessions FROM anon, authenticated;
```

### Archetype F: Pre-Authentication Isolation (`otp_challenges`)

```sql
ALTER TABLE public.otp_challenges ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.otp_challenges;
CREATE POLICY service_role_all ON public.otp_challenges
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Strictly revoke all client access
REVOKE ALL ON public.otp_challenges FROM anon, authenticated;
```

---

## 3. Hardened Context Helper Functions

```sql
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(
        -- 1. PostgREST verified JWT claim
        nullif(current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'org_id', '')::uuid,
        -- 2. Authoritative profile lookup via authenticated UID
        (SELECT org_id FROM public.users WHERE auth_user_id = auth.uid() OR id = auth.uid() LIMIT 1),
        -- 3. Backend transaction-scoped local setting (SET LOCAL)
        nullif(current_setting('app.current_org_id', true), '')::uuid
    );
$$;

CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(
        -- 1. PostgREST verified JWT claim
        (current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'role') = 'SUPER_ADMIN',
        -- 2. Authoritative database profile role
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE (auth_user_id = auth.uid() OR id = auth.uid()) 
              AND role = 'SUPER_ADMIN' 
              AND status = 'ACTIVE'
        ),
        -- 3. Backend local setting (only permitted under postgres or service_role)
        (current_setting('app.is_super_admin', true) = 'true' AND current_user IN ('postgres', 'service_role')),
        false
    );
$$;
```

---

## 4. Grant Architecture & PostgREST Surface Hardening

```sql
-- 1. Revoke dangerous TRUNCATE and all access from anon
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- 2. Restrict authenticated role to CRUD, explicitly revoking TRUNCATE
REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- 3. Grant full application access to service_role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;

-- 4. Default privileges for future schema objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
```
