-- =============================================================================
-- AGENTGUARD DEFENSE-IN-DEPTH POSTGRESQL ROW-LEVEL SECURITY (RLS) MIGRATION
-- Migration Revision: 20261125010000_idempotent_defense_in_depth_rls
-- Target Engine: PostgreSQL 15+ / Supabase PostgreSQL 17.6+
-- Idempotent: YES (Safe to re-run; uses DROP POLICY IF EXISTS before CREATE)
-- Transactional: Wrapped in BEGIN ... COMMIT
-- Remediated: Incorporates all 6 independent audit security corrections
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. HARDENED HELPER FUNCTIONS & TENANT CONTEXT RESOLUTION
-- -----------------------------------------------------------------------------
-- Removes untrusted GUC spoofing paths. For client PostgREST roles, identity
-- is resolved strictly from verified JWT claims or authoritative database profiles.
-- Backend transaction-scoped GUCs are honored only for trusted service roles.

CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS uuid
LANGUAGE sql
STABLE
SET search_path = public, auth, pg_temp
AS $$
    SELECT CASE
        -- 1. Trusted backend role: permit transaction-scoped GUC or JWT context
        WHEN CURRENT_USER IN ('postgres', 'service_role') THEN
            COALESCE(
                nullif(current_setting('app.current_org_id', true), '')::uuid,
                nullif((nullif(current_setting('request.jwt.claims', true), ''))::jsonb -> 'app_metadata' ->> 'org_id', '')::uuid
            )
        -- 2. Authenticated PostgREST client: resolve strictly from verified JWT app_metadata
        WHEN CURRENT_USER = 'authenticated' THEN
            nullif((nullif(current_setting('request.jwt.claims', true), ''))::jsonb -> 'app_metadata' ->> 'org_id', '')::uuid
        -- 3. Anonymous or untrusted roles fail closed
        ELSE NULL
    END;
$$;

CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = public, auth, pg_temp
AS $$
    SELECT CASE
        -- 1. Trusted backend role: permit transaction-scoped GUC or JWT context
        WHEN CURRENT_USER IN ('postgres', 'service_role') THEN
            COALESCE(
                current_setting('app.is_super_admin', true) = 'true',
                ((nullif(current_setting('request.jwt.claims', true), ''))::jsonb -> 'app_metadata' ->> 'role') = 'SUPER_ADMIN',
                false
            )
        -- 2. Authenticated PostgREST client: check verified JWT app_metadata
        WHEN CURRENT_USER = 'authenticated' THEN
            COALESCE(
                ((nullif(current_setting('request.jwt.claims', true), ''))::jsonb -> 'app_metadata' ->> 'role') = 'SUPER_ADMIN',
                false
            )
        -- 3. Anonymous or untrusted roles fail closed
        ELSE false
    END;
$$;

-- Grant execution permissions on helper functions
REVOKE ALL ON FUNCTION public.current_org_id() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.is_super_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.current_org_id() TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.is_super_admin() TO anon, authenticated, service_role;


-- -----------------------------------------------------------------------------
-- 2. DIRECT TENANT-BEARING TABLES (org_id column NOT NULL)
-- -----------------------------------------------------------------------------

-- Table: organizations (Tenant boundary root)
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_role_all_organizations ON public.organizations;
CREATE POLICY service_role_all_organizations ON public.organizations FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS tenant_isolation_organizations ON public.organizations;
CREATE POLICY tenant_isolation_organizations ON public.organizations FOR ALL TO authenticated
    USING (id = public.current_org_id() OR public.is_super_admin())
    WITH CHECK (id = public.current_org_id() OR public.is_super_admin());

-- Standard direct org_id tables (strictly non-nullable org_id)
DO $$
DECLARE
    tbl text;
    direct_tables text[] := ARRAY[
        'agents',
        'users',
        'api_keys',
        'policies',
        'webhook_endpoints',
        'scheduled_reports',
        'report_histories',
        'security_incidents',
        'runtime_risk_signals',
        'sandbox_execution_jobs',
        'agent_budget_configs',
        'agent_executions',
        'evaluation_datasets',
        'evaluation_dataset_records',
        'evaluation_scenarios',
        'evaluation_scenario_records',
        'siem_deliveries',
        'user_invitations',
        'licenses',
        'license_usages',
        'guardrail_rules',
        'integration_configs',
        'network_policies',
        'optimization_rules'
    ];
BEGIN
    FOREACH tbl IN ARRAY direct_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
            
            -- Service role bypass
            EXECUTE format('DROP POLICY IF EXISTS service_role_all ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY service_role_all ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true);', tbl);
            
            -- Authenticated tenant isolation policy
            EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY tenant_isolation ON public.%I FOR ALL TO authenticated USING (org_id = public.current_org_id() OR public.is_super_admin()) WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());', tbl);
        END IF;
    END LOOP;
END $$;


-- -----------------------------------------------------------------------------
-- 3. REMEDIATED AUDIT LOGS (Defect 1: Immutable Audit Trail)
-- -----------------------------------------------------------------------------
-- Authenticated users can SELECT only their authorized tenant's audit trail.
-- INSERT is allowed strictly with tenant matching.
-- CRITICAL: Zero UPDATE or DELETE policies are created for authenticated role.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'audit_logs') THEN
        ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.audit_logs;
        CREATE POLICY service_role_all ON public.audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
        
        DROP POLICY IF EXISTS tenant_read_audit_logs ON public.audit_logs;
        CREATE POLICY tenant_read_audit_logs ON public.audit_logs FOR SELECT TO authenticated
            USING (org_id = public.current_org_id() OR public.is_super_admin());
            
        DROP POLICY IF EXISTS tenant_insert_audit_logs ON public.audit_logs;
        CREATE POLICY tenant_insert_audit_logs ON public.audit_logs FOR INSERT TO authenticated
            WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());
            
        -- Explicitly drop any lingering permissive policies
        DROP POLICY IF EXISTS tenant_isolation ON public.audit_logs;
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 4. REMEDIATED GLOBAL TOOLS & SIEM CONFIGS (Defect 2: Global Table Support)
-- -----------------------------------------------------------------------------
-- Global tools (org_id IS NULL) must be readable by all authenticated users,
-- but tenants can only insert, update, or delete their own custom tools.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tools') THEN
        ALTER TABLE public.tools ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.tools;
        CREATE POLICY service_role_all ON public.tools FOR ALL TO service_role USING (true) WITH CHECK (true);
        
        DROP POLICY IF EXISTS tenant_read_tools ON public.tools;
        CREATE POLICY tenant_read_tools ON public.tools FOR SELECT TO authenticated
            USING (org_id = public.current_org_id() OR org_id IS NULL OR public.is_super_admin());
            
        DROP POLICY IF EXISTS tenant_modify_tools ON public.tools;
        CREATE POLICY tenant_modify_tools ON public.tools FOR ALL TO authenticated
            USING (org_id = public.current_org_id() OR public.is_super_admin())
            WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());
            
        DROP POLICY IF EXISTS tenant_isolation ON public.tools;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'siem_configs') THEN
        ALTER TABLE public.siem_configs ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.siem_configs;
        CREATE POLICY service_role_all ON public.siem_configs FOR ALL TO service_role USING (true) WITH CHECK (true);
        
        DROP POLICY IF EXISTS tenant_read_siem ON public.siem_configs;
        CREATE POLICY tenant_read_siem ON public.siem_configs FOR SELECT TO authenticated
            USING (org_id = public.current_org_id() OR (org_id IS NULL AND public.is_super_admin()) OR public.is_super_admin());
            
        DROP POLICY IF EXISTS tenant_write_siem ON public.siem_configs;
        CREATE POLICY tenant_write_siem ON public.siem_configs FOR ALL TO authenticated
            USING (org_id = public.current_org_id() OR public.is_super_admin())
            WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());
            
        DROP POLICY IF EXISTS tenant_isolation ON public.siem_configs;
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 5. REMEDIATED AGENT RELATIONSHIPS (Defect 3: Dual-Agent Validation)
-- -----------------------------------------------------------------------------
-- Validates both parent_agent_id AND child_agent_id belong to authorized tenant.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'agent_relationships') THEN
        ALTER TABLE public.agent_relationships ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.agent_relationships;
        CREATE POLICY service_role_all ON public.agent_relationships FOR ALL TO service_role USING (true) WITH CHECK (true);

        DROP POLICY IF EXISTS tenant_isolation ON public.agent_relationships;
        CREATE POLICY tenant_isolation ON public.agent_relationships FOR ALL TO authenticated
            USING (
                public.is_super_admin()
                OR (
                    EXISTS (
                        SELECT 1 FROM public.agents
                        WHERE public.agents.id = public.agent_relationships.parent_agent_id
                          AND public.agents.org_id = public.current_org_id()
                    )
                    AND EXISTS (
                        SELECT 1 FROM public.agents
                        WHERE public.agents.id = public.agent_relationships.child_agent_id
                          AND public.agents.org_id = public.current_org_id()
                    )
                )
            )
            WITH CHECK (
                public.is_super_admin()
                OR (
                    EXISTS (
                        SELECT 1 FROM public.agents
                        WHERE public.agents.id = public.agent_relationships.parent_agent_id
                          AND public.agents.org_id = public.current_org_id()
                    )
                    AND EXISTS (
                        SELECT 1 FROM public.agents
                        WHERE public.agents.id = public.agent_relationships.child_agent_id
                          AND public.agents.org_id = public.current_org_id()
                    )
                )
            );
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 6. REMEDIATED SESSIONS (Defect 4: Token Exposure Lockdown)
-- -----------------------------------------------------------------------------
-- Sessions store sensitive JWT tokens and refresh secrets.
-- Access is restricted strictly to trusted service role. Client PostgREST is revoked.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sessions') THEN
        ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.sessions;
        CREATE POLICY service_role_all ON public.sessions FOR ALL TO service_role USING (true) WITH CHECK (true);
        
        DROP POLICY IF EXISTS tenant_isolation ON public.sessions;
        
        -- Revoke client direct access completely
        REVOKE ALL ON public.sessions FROM anon, authenticated;
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 7. REMEDIATED DECISIONS (Defect 5: Symmetric Polymorphic Validation)
-- -----------------------------------------------------------------------------
-- Harmonizes USING and WITH CHECK to support human and agent decisions,
-- while rejecting conflicting cross-tenant ownership.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'decisions') THEN
        ALTER TABLE public.decisions ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.decisions;
        CREATE POLICY service_role_all ON public.decisions FOR ALL TO service_role USING (true) WITH CHECK (true);

        DROP POLICY IF EXISTS tenant_isolation ON public.decisions;
        CREATE POLICY tenant_isolation ON public.decisions FOR ALL TO authenticated
            USING (
                public.is_super_admin()
                OR (
                    -- Case 1: Agent decision (agent must belong to current tenant)
                    (
                        public.decisions.agent_id IS NOT NULL
                        AND EXISTS (
                            SELECT 1 FROM public.agents
                            WHERE public.agents.id = public.decisions.agent_id
                              AND public.agents.org_id = public.current_org_id()
                        )
                    )
                    AND
                    -- If user_id is also supplied, user must also belong to current tenant
                    (
                        public.decisions.user_id IS NULL
                        OR EXISTS (
                            SELECT 1 FROM public.users
                            WHERE public.users.id = public.decisions.user_id
                              AND public.users.org_id = public.current_org_id()
                        )
                    )
                )
                OR (
                    -- Case 2: Human-only decision (user must belong to current tenant)
                    public.decisions.agent_id IS NULL
                    AND public.decisions.user_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM public.users
                        WHERE public.users.id = public.decisions.user_id
                          AND public.users.org_id = public.current_org_id()
                    )
                )
            )
            WITH CHECK (
                public.is_super_admin()
                OR (
                    -- Case 1: Agent decision
                    (
                        public.decisions.agent_id IS NOT NULL
                        AND EXISTS (
                            SELECT 1 FROM public.agents
                            WHERE public.agents.id = public.decisions.agent_id
                              AND public.agents.org_id = public.current_org_id()
                        )
                    )
                    AND
                    (
                        public.decisions.user_id IS NULL
                        OR EXISTS (
                            SELECT 1 FROM public.users
                            WHERE public.users.id = public.decisions.user_id
                              AND public.users.org_id = public.current_org_id()
                        )
                    )
                )
                OR (
                    -- Case 2: Human-only decision
                    public.decisions.agent_id IS NULL
                    AND public.decisions.user_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM public.users
                        WHERE public.users.id = public.decisions.user_id
                          AND public.users.org_id = public.current_org_id()
                    )
                )
            );
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 8. PARENT-CHILD TENANT TABLES (Agent, Webhook, Policy & User Children)
-- -----------------------------------------------------------------------------

-- Standard Agent Child Tables
DO $$
DECLARE
    tbl text;
    agent_child_tables text[] := ARRAY[
        'agent_credentials',
        'agent_passports',
        'agent_runtime_sessions',
        'anomaly_events',
        'approval_requests',
        'behavior_profiles',
        'budgets',
        'capability_tokens',
        'circuit_breakers',
        'permissions',
        'provenance_events',
        'reputation_scores',
        'resource_usages',
        'risk_scores',
        'security_tests',
        'simulations',
        'transactions'
    ];
BEGIN
    FOREACH tbl IN ARRAY agent_child_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
            
            -- Service role bypass
            EXECUTE format('DROP POLICY IF EXISTS service_role_all ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY service_role_all ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true);', tbl);
            
            -- Tenant isolation through parent agent
            EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY tenant_isolation ON public.%I FOR ALL TO authenticated USING (public.is_super_admin() OR EXISTS (SELECT 1 FROM public.agents WHERE public.agents.id = public.%I.agent_id AND public.agents.org_id = public.current_org_id())) WITH CHECK (public.is_super_admin() OR EXISTS (SELECT 1 FROM public.agents WHERE public.agents.id = public.%I.agent_id AND public.agents.org_id = public.current_org_id()));', tbl, tbl, tbl);
        END IF;
    END LOOP;
END $$;

-- Notifications (Scoped per-user within tenant to prevent cross-user snooping)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'notifications') THEN
        ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS service_role_all ON public.notifications;
        CREATE POLICY service_role_all ON public.notifications FOR ALL TO service_role USING (true) WITH CHECK (true);

        DROP POLICY IF EXISTS tenant_isolation ON public.notifications;
        CREATE POLICY tenant_isolation ON public.notifications FOR ALL TO authenticated
            USING (
                public.is_super_admin()
                OR (
                    public.notifications.user_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM public.users
                        WHERE public.users.id = public.notifications.user_id
                          AND (public.users.auth_user_id = auth.uid()::text OR public.users.id = auth.uid())
                          AND public.users.org_id = public.current_org_id()
                    )
                )
            )
            WITH CHECK (
                public.is_super_admin()
                OR (
                    public.notifications.user_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM public.users
                        WHERE public.users.id = public.notifications.user_id
                          AND public.users.org_id = public.current_org_id()
                    )
                )
            );
    END IF;
END $$;

-- Webhook Deliveries (Child of webhook_endpoints)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'webhook_deliveries') THEN
        ALTER TABLE public.webhook_deliveries ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS service_role_all ON public.webhook_deliveries;
        CREATE POLICY service_role_all ON public.webhook_deliveries FOR ALL TO service_role USING (true) WITH CHECK (true);

        DROP POLICY IF EXISTS tenant_isolation ON public.webhook_deliveries;
        CREATE POLICY tenant_isolation ON public.webhook_deliveries FOR ALL TO authenticated
            USING (
                public.is_super_admin()
                OR EXISTS (
                    SELECT 1 FROM public.webhook_endpoints
                    WHERE public.webhook_endpoints.id = public.webhook_deliveries.webhook_id
                      AND public.webhook_endpoints.org_id = public.current_org_id()
                )
            )
            WITH CHECK (
                public.is_super_admin()
                OR EXISTS (
                    SELECT 1 FROM public.webhook_endpoints
                    WHERE public.webhook_endpoints.id = public.webhook_deliveries.webhook_id
                      AND public.webhook_endpoints.org_id = public.current_org_id()
                )
            );
    END IF;
END $$;

-- Policy Rules (Child of policies)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'policy_rules') THEN
        ALTER TABLE public.policy_rules ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS service_role_all ON public.policy_rules;
        CREATE POLICY service_role_all ON public.policy_rules FOR ALL TO service_role USING (true) WITH CHECK (true);

        DROP POLICY IF EXISTS tenant_isolation ON public.policy_rules;
        CREATE POLICY tenant_isolation ON public.policy_rules FOR ALL TO authenticated
            USING (
                public.is_super_admin()
                OR EXISTS (
                    SELECT 1 FROM public.policies
                    WHERE public.policies.id = public.policy_rules.policy_id
                      AND public.policies.org_id = public.current_org_id()
                )
            )
            WITH CHECK (
                public.is_super_admin()
                OR EXISTS (
                    SELECT 1 FROM public.policies
                    WHERE public.policies.id = public.policy_rules.policy_id
                      AND public.policies.org_id = public.current_org_id()
                )
            );
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 9. GLOBAL REFERENCE CATALOGS & PRE-AUTH OTP TABLE (Defect 6: Pre-Auth Lockdown)
-- -----------------------------------------------------------------------------

-- Global Catalogs (plans, ai_models, capabilities, model_pricing)
DO $$
DECLARE
    tbl text;
    global_tables text[] := ARRAY['plans', 'ai_models', 'capabilities', 'model_pricing'];
BEGIN
    FOREACH tbl IN ARRAY global_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
            
            EXECUTE format('DROP POLICY IF EXISTS service_role_all ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY service_role_all ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true);', tbl);
            
            EXECUTE format('DROP POLICY IF EXISTS authenticated_read_only ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY authenticated_read_only ON public.%I FOR SELECT TO authenticated USING (true);', tbl);
            
            EXECUTE format('DROP POLICY IF EXISTS super_admin_write ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY super_admin_write ON public.%I FOR ALL TO authenticated USING (public.is_super_admin()) WITH CHECK (public.is_super_admin());', tbl);
        END IF;
    END LOOP;
END $$;

-- OTP Challenges (Pre-auth cryptographic verification table)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'otp_challenges') THEN
        ALTER TABLE public.otp_challenges ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.otp_challenges;
        CREATE POLICY service_role_all ON public.otp_challenges FOR ALL TO service_role USING (true) WITH CHECK (true);
        
        DROP POLICY IF EXISTS tenant_isolation ON public.otp_challenges;
        
        -- Strictly revoke client PostgREST access
        REVOKE ALL ON public.otp_challenges FROM anon, authenticated;
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 10. POSTGREST PRIVILEGE HARDENING & DANGEROUS PERMISSION REVOCATION
-- -----------------------------------------------------------------------------
-- Eliminates TRUNCATE, REFERENCES, and TRIGGER grants from anon and authenticated.

-- 1. Strip anon privileges completely
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- 2. Strip dangerous TRUNCATE, REFERENCES, TRIGGER from authenticated
REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM authenticated;

-- 3. Grant scoped CRUD to authenticated (governed by RLS policies above)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- 4. Specifically enforce table-level write denials for sensitive/immutable tables
REVOKE UPDATE, DELETE ON public.audit_logs FROM authenticated;
REVOKE ALL ON public.sessions FROM anon, authenticated;
REVOKE ALL ON public.otp_challenges FROM anon, authenticated;

-- 5. Full application access for trusted service_role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;

-- 6. Default privileges for future schema objects created under postgres role
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;

COMMIT;
