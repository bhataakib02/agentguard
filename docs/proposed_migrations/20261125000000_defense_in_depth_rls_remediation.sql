-- ============================================================================
-- PROPOSED MIGRATION: AGENTGUARD Defense-in-Depth RLS & Permission Hardening
-- Status: PROPOSED FOR ARCHITECTURAL REVIEW ONLY — DO NOT EXECUTE DIRECTLY
-- Safety: Read-only audit confirmed 0 RLS policies on live public schema.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- STEP 1: Revoke Excessive Privileges from Supabase PostgREST Roles
-- Removes TRUNCATE, TRIGGER, REFERENCES from anon and authenticated roles.
-- Ensures zero direct PostgREST access to AgentGuard internal application tables.
-- ----------------------------------------------------------------------------

DO $$
DECLARE
    tbl text;
    app_tables text[] := ARRAY[
        'agent_budget_configs', 'agent_credentials', 'agent_executions', 'agent_passports',
        'agent_relationships', 'agent_runtime_sessions', 'agents', 'ai_models',
        'anomaly_events', 'api_keys', 'approval_requests', 'audit_logs',
        'behavior_profiles', 'budgets', 'capabilities', 'capability_tokens',
        'circuit_breakers', 'decisions', 'evaluation_dataset_records', 'evaluation_datasets',
        'license_usages', 'licenses', 'model_pricing', 'notifications',
        'organizations', 'permissions', 'plans', 'policies', 'policy_rules',
        'provenance_events', 'report_histories', 'reputation_scores', 'resource_usages',
        'risk_scores', 'runtime_risk_signals', 'sandbox_execution_jobs', 'scheduled_reports',
        'security_incidents', 'security_tests', 'sessions', 'siem_configs',
        'siem_deliveries', 'simulations', 'tools', 'transactions', 'user_invitations',
        'users', 'webhook_deliveries', 'webhook_endpoints', 'otp_challenges'
    ];
BEGIN
    FOREACH tbl IN ARRAY app_tables LOOP
        IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = tbl) THEN
            EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated;', tbl);
        END IF;
    END LOOP;
END $$;

-- Alter Default Privileges so future tables created by postgres in public do not grant Dxtm to client roles
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- STEP 2: Enable Row Level Security (RLS) on All Tenant-Scoped Tables
-- ----------------------------------------------------------------------------

DO $$
DECLARE
    tbl text;
    tenant_tables text[] := ARRAY[
        'organizations', 'users', 'sessions', 'agents', 'agent_passports',
        'permissions', 'capability_tokens', 'policies', 'policy_rules',
        'decisions', 'approval_requests', 'audit_logs', 'circuit_breakers',
        'api_keys', 'licenses', 'license_usages', 'evaluation_datasets',
        'evaluation_dataset_records', 'security_incidents', 'security_tests',
        'report_histories', 'scheduled_reports', 'siem_configs', 'siem_deliveries',
        'sandbox_execution_jobs', 'webhook_endpoints', 'webhook_deliveries',
        'agent_credentials', 'agent_budget_configs', 'agent_executions',
        'runtime_risk_signals', 'notifications', 'otp_challenges'
    ];
BEGIN
    FOREACH tbl IN ARRAY tenant_tables LOOP
        IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = tbl) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
            EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY;', tbl);
        END IF;
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- STEP 3: Explicit Deny-All Policies for PostgREST Client Roles
-- Prevents data exfiltration even if table grants are inadvertently reintroduced.
-- ----------------------------------------------------------------------------

DO $$
DECLARE
    tbl text;
    tenant_tables text[] := ARRAY[
        'organizations', 'users', 'sessions', 'agents', 'agent_passports',
        'permissions', 'capability_tokens', 'policies', 'policy_rules',
        'decisions', 'approval_requests', 'audit_logs', 'circuit_breakers',
        'api_keys', 'licenses', 'license_usages', 'evaluation_datasets',
        'evaluation_dataset_records', 'security_incidents', 'security_tests',
        'report_histories', 'scheduled_reports', 'siem_configs', 'siem_deliveries',
        'sandbox_execution_jobs', 'webhook_endpoints', 'webhook_deliveries',
        'agent_credentials', 'agent_budget_configs', 'agent_executions',
        'runtime_risk_signals', 'notifications', 'otp_challenges'
    ];
BEGIN
    FOREACH tbl IN ARRAY tenant_tables LOOP
        IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = tbl) THEN
            EXECUTE format('DROP POLICY IF EXISTS deny_client_access ON public.%I;', tbl);
            EXECUTE format('CREATE POLICY deny_client_access ON public.%I FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);', tbl);
        END IF;
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- STEP 4: Defense-in-Depth Tenant Isolation for Application Roles
-- Evaluated when backend connects via non-bypassrls role or enforces session context.
-- ----------------------------------------------------------------------------

-- Organizations: users only access their own organization or SUPER_ADMIN
CREATE POLICY app_tenant_isolation_organizations ON public.organizations
    FOR ALL
    USING (
        id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    )
    WITH CHECK (
        id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    );

-- Users: users only access members of their organization or SUPER_ADMIN
CREATE POLICY app_tenant_isolation_users ON public.users
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    )
    WITH CHECK (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    );

-- Agents: agents bound strictly to organization
CREATE POLICY app_tenant_isolation_agents ON public.agents
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    )
    WITH CHECK (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    );

-- Audit Logs: immutable audit events bound to organization
CREATE POLICY app_tenant_isolation_audit_logs ON public.audit_logs
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    )
    WITH CHECK (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
        OR current_user = 'postgres'
    );

COMMIT;
