-- =============================================================================
-- AGENTGUARD DEFENSE-IN-DEPTH POSTGRESQL ROW-LEVEL SECURITY (RLS) MIGRATION
-- Migration Revision: 20261125010000_idempotent_defense_in_depth_rls
-- Target Engine: PostgreSQL 15+ / Supabase PostgreSQL
-- Idempotent: YES (Safe to re-run; uses DROP POLICY IF EXISTS before CREATE)
-- Transactional: Wrapped in BEGIN ... COMMIT
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. HELPER FUNCTIONS & TENANT CONTEXT SETTERS
-- -----------------------------------------------------------------------------

-- Securely extract the current tenant organization UUID from session/local settings.
-- Returns NULL if the setting is unset or empty string, preventing cast exceptions.
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT nullif(current_setting('app.current_org_id', true), '')::uuid;
$$;

-- Check whether the current execution context has verified SUPER_ADMIN privileges.
CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(current_setting('app.is_super_admin', true) = 'true', false);
$$;

-- Grant execution permissions on helper functions to standard database roles
GRANT EXECUTE ON FUNCTION public.current_org_id() TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.is_super_admin() TO anon, authenticated, service_role;


-- -----------------------------------------------------------------------------
-- 2. DIRECT TENANT-BEARING TABLES (org_id column present)
-- -----------------------------------------------------------------------------

-- Table: organizations (Tenant boundary root)
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_role_all_organizations ON public.organizations;
CREATE POLICY service_role_all_organizations ON public.organizations FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS tenant_isolation_organizations ON public.organizations;
CREATE POLICY tenant_isolation_organizations ON public.organizations FOR ALL TO authenticated
    USING (id = public.current_org_id() OR public.is_super_admin())
    WITH CHECK (id = public.current_org_id() OR public.is_super_admin());

-- Macro helper for standard direct org_id tables:
-- agents, users, api_keys, audit_logs, policies, tools, webhook_endpoints,
-- scheduled_reports, report_histories, security_incidents, runtime_risk_signals,
-- sandbox_execution_jobs, agent_budget_configs, agent_executions, evaluation_datasets,
-- evaluation_dataset_records, evaluation_scenarios, evaluation_scenario_records,
-- siem_configs, siem_deliveries, user_invitations, licenses, license_usages,
-- guardrail_rules, integration_configs, network_policies, optimization_rules

DO $$
DECLARE
    tbl text;
    direct_tables text[] := ARRAY[
        'agents',
        'users',
        'api_keys',
        'audit_logs',
        'policies',
        'tools',
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
        'siem_configs',
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
            
            -- Tenant isolation policy
            EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY tenant_isolation ON public.%I FOR ALL TO authenticated USING (org_id = public.current_org_id() OR public.is_super_admin()) WITH CHECK (org_id = public.current_org_id() OR public.is_super_admin());', tbl);
        END IF;
    END LOOP;
END $$;


-- -----------------------------------------------------------------------------
-- 3. PARENT-CHILD TENANT TABLES (Inherited tenant via parent FK)
-- -----------------------------------------------------------------------------

-- Decisions (Children of agents or users)
IF_EXISTS_DECISIONS:
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
    END IF;
END $$;

-- Agent Child Tables (agent_credentials, agent_passports, agent_relationships,
-- agent_runtime_sessions, anomaly_events, approval_requests, behavior_profiles,
-- budgets, capability_tokens, circuit_breakers, permissions, provenance_events,
-- reputation_scores, resource_usages, risk_scores, security_tests, simulations, transactions)

DO $$
DECLARE
    tbl text;
    agent_child_tables text[] := ARRAY[
        'agent_credentials',
        'agent_passports',
        'agent_runtime_sessions',
        'anomaly_events',
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
            
            -- Tenant isolation through agent parent
            EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY tenant_isolation ON public.%I FOR ALL TO authenticated USING (public.is_super_admin() OR EXISTS (SELECT 1 FROM public.agents WHERE public.agents.id = public.%I.agent_id AND public.agents.org_id = public.current_org_id())) WITH CHECK (public.is_super_admin() OR EXISTS (SELECT 1 FROM public.agents WHERE public.agents.id = public.%I.agent_id AND public.agents.org_id = public.current_org_id()));', tbl, tbl, tbl);
        END IF;
    END LOOP;
END $$;

-- Agent Relationships (special case with parent_agent_id and child_agent_id)
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
                OR EXISTS (
                    SELECT 1 FROM public.agents
                    WHERE public.agents.id = public.agent_relationships.parent_agent_id
                      AND public.agents.org_id = public.current_org_id()
                )
            )
            WITH CHECK (
                public.is_super_admin()
                OR EXISTS (
                    SELECT 1 FROM public.agents
                    WHERE public.agents.id = public.agent_relationships.parent_agent_id
                      AND public.agents.org_id = public.current_org_id()
                )
            );
    END IF;
END $$;

-- Approval Requests (linked to decisions and agents)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'approval_requests') THEN
        ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS service_role_all ON public.approval_requests;
        CREATE POLICY service_role_all ON public.approval_requests FOR ALL TO service_role USING (true) WITH CHECK (true);

        DROP POLICY IF EXISTS tenant_isolation ON public.approval_requests;
        CREATE POLICY tenant_isolation ON public.approval_requests FOR ALL TO authenticated
            USING (
                public.is_super_admin()
                OR EXISTS (
                    SELECT 1 FROM public.agents
                    WHERE public.agents.id = public.approval_requests.agent_id
                      AND public.agents.org_id = public.current_org_id()
                )
            )
            WITH CHECK (
                public.is_super_admin()
                OR EXISTS (
                    SELECT 1 FROM public.agents
                    WHERE public.agents.id = public.approval_requests.agent_id
                      AND public.agents.org_id = public.current_org_id()
                )
            );
    END IF;
END $$;

-- User Child Tables: sessions, notifications
DO $$
DECLARE
    tbl text;
    user_child_tables text[] := ARRAY['sessions', 'notifications'];
BEGIN
    FOREACH tbl IN ARRAY user_child_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
            
            -- Service role bypass
            EXECUTE format('DROP POLICY IF EXISTS service_role_all ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY service_role_all ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true);', tbl);
            
            -- Tenant isolation through user parent
            EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY tenant_isolation ON public.%I FOR ALL TO authenticated USING (public.is_super_admin() OR EXISTS (SELECT 1 FROM public.users WHERE public.users.id = public.%I.user_id AND public.users.org_id = public.current_org_id())) WITH CHECK (public.is_super_admin() OR EXISTS (SELECT 1 FROM public.users WHERE public.users.id = public.%I.user_id AND public.users.org_id = public.current_org_id()));', tbl, tbl, tbl);
        END IF;
    END LOOP;
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
-- 4. GLOBAL REFERENCE CATALOGS & SYSTEM TABLES
-- -----------------------------------------------------------------------------

-- Global Reference Tables: plans, ai_models, capabilities, model_pricing
-- These are readable by all authenticated users, writable only by service_role/super_admin.
DO $$
DECLARE
    tbl text;
    global_tables text[] := ARRAY['plans', 'ai_models', 'capabilities', 'model_pricing'];
BEGIN
    FOREACH tbl IN ARRAY global_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
            
            -- Service role full access
            EXECUTE format('DROP POLICY IF EXISTS service_role_all ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY service_role_all ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true);', tbl);
            
            -- Authenticated users read-only
            EXECUTE format('DROP POLICY IF EXISTS authenticated_read_only ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY authenticated_read_only ON public.%I FOR SELECT TO authenticated USING (true);', tbl);
            
            -- Super admin modification
            EXECUTE format('DROP POLICY IF EXISTS super_admin_write ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY super_admin_write ON public.%I FOR ALL TO authenticated USING (public.is_super_admin()) WITH CHECK (public.is_super_admin());', tbl);
        END IF;
    END LOOP;
END $$;

-- OTP Challenges (Pre-auth and step-up authentication table)
-- Must NOT be accessible directly via PostgREST client keys. Backend service_role exclusive.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'otp_challenges') THEN
        ALTER TABLE public.otp_challenges ENABLE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS service_role_all ON public.otp_challenges;
        CREATE POLICY service_role_all ON public.otp_challenges FOR ALL TO service_role USING (true) WITH CHECK (true);
        
        -- Revoke direct PostgREST client access completely
        REVOKE ALL ON public.otp_challenges FROM anon, authenticated;
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 5. POSTGREST CLIENT PRIVILEGE HARDENING
-- -----------------------------------------------------------------------------

-- Ensure anon cannot read or modify any application tables in public schema
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- Restrict authenticated role to CRUD subject to RLS policies
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- Ensure service_role has full access for backend application operations
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;

-- Default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;

COMMIT;
