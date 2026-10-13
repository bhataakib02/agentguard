-- AGENTGUARD Controlled Database Reset & Maintenance Script
-- STRICT SAFETY CONTROLS:
-- 1. This script FAILS CLOSED unless explicitly authorized by setting:
--      SET agentguard.destructive_maintenance_confirmed = 'YES_DELETE_ALL_DATA';
-- 2. Never run against a live production database with active customers.
-- 3. The Super Admin email must be supplied via session variable or explicitly declared:
--      SET agentguard.preserve_admin_email = 'admin@yourcompany.com';

DO $$
DECLARE
    confirmed_flag text;
    target_admin_email text;
    sa_auth_id UUID;
    sa_public_id UUID;
    curr_db text := current_database();
    allowed_dbs text[] := ARRAY['agentguard_dev', 'agentguard_test', 'agentguard_local', 'agentguard_ci', 'test_agentguard'];
    env_guard text;
BEGIN
    -- 1. FAIL-CLOSED ALLOWLIST GUARD: Unknown and unapproved databases are rejected by default
    IF NOT (curr_db = ANY(allowed_dbs)) THEN
        RAISE EXCEPTION 'CRITICAL SAFETY ABORT: Database "%" is not in the approved non-production allowlist (%). Unknown and production databases are rejected by default.', curr_db, array_to_string(allowed_dbs, ', ');
    END IF;

    -- 2. INDEPENDENT ENVIRONMENT GUARD: System environment must be explicitly non-production
    BEGIN
        env_guard := current_setting('agentguard.environment', true);
    EXCEPTION WHEN OTHERS THEN
        env_guard := NULL;
    END;

    IF env_guard IS NULL OR env_guard NOT IN ('development', 'test', 'local', 'ci') THEN
        RAISE EXCEPTION 'CRITICAL SAFETY ABORT: Independent environment guard failed. agentguard.environment must be explicitly set to development, test, local, or ci (current: "%").', coalesce(env_guard, 'UNSET');
    END IF;

    -- 3. EXPLICIT OPERATOR CONFIRMATION: Require explicit confirmation setting
    BEGIN
        confirmed_flag := current_setting('agentguard.destructive_maintenance_confirmed', true);
    EXCEPTION WHEN OTHERS THEN
        confirmed_flag := NULL;
    END;

    IF confirmed_flag IS NULL OR confirmed_flag <> 'YES_DELETE_ALL_DATA' THEN
        RAISE EXCEPTION 'SAFETY ABORT: Destructive maintenance requires explicit confirmation. Execute: SET agentguard.destructive_maintenance_confirmed = ''YES_DELETE_ALL_DATA''; prior to running.';
    END IF;

    -- 2. RESOLVE TARGET ADMIN EMAIL (Configurable, never hardcoded personal email)
    BEGIN
        target_admin_email := current_setting('agentguard.preserve_admin_email', true);
    EXCEPTION WHEN OTHERS THEN
        target_admin_email := NULL;
    END;

    IF target_admin_email IS NULL OR target_admin_email = '' THEN
        -- Resolve the first existing SUPER_ADMIN account
        SELECT email INTO target_admin_email FROM public.users WHERE role = 'SUPER_ADMIN' AND status = 'ACTIVE' LIMIT 1;
        IF target_admin_email IS NULL THEN
            RAISE EXCEPTION 'SAFETY ABORT: No active SUPER_ADMIN account found in public.users to preserve!';
        END IF;
    END IF;

    -- 3. RESOLVE PRESERVED ADMIN IDENTITY
    SELECT id INTO sa_auth_id FROM auth.users WHERE email = target_admin_email;
    SELECT id INTO sa_public_id FROM public.users WHERE email = target_admin_email;

    IF sa_public_id IS NULL THEN
        RAISE EXCEPTION 'SAFETY ABORT: Preserved Admin account (%) not found in public.users!', target_admin_email;
    END IF;

    RAISE NOTICE 'Preserving Super Admin (%). Public ID: %, Auth ID: %', target_admin_email, sa_public_id, sa_auth_id;

    -- 4. Detach Super Admin from tenant organization and ensure active status
    UPDATE public.users 
    SET org_id = NULL, 
        role = 'SUPER_ADMIN', 
        status = 'ACTIVE' 
    WHERE id = sa_public_id;

    -- 5. Purge tenant data in foreign-key safe dependency order
    DELETE FROM public.provenance_events;
    DELETE FROM public.approval_requests;
    DELETE FROM public.decisions;
    DELETE FROM public.capability_tokens;
    DELETE FROM public.permissions;
    DELETE FROM public.agent_passports;
    DELETE FROM public.agent_credentials;
    DELETE FROM public.risk_scores;
    DELETE FROM public.behavior_profiles;
    DELETE FROM public.reputation_scores;
    DELETE FROM public.circuit_breakers;
    DELETE FROM public.budgets;
    DELETE FROM public.transactions;
    DELETE FROM public.security_tests;
    DELETE FROM public.simulations;
    DELETE FROM public.resource_usages;
    DELETE FROM public.anomaly_events;
    DELETE FROM public.security_incidents;
    DELETE FROM public.agent_relationships;
    DELETE FROM public.agents;
    DELETE FROM public.policy_rules;
    DELETE FROM public.policies;
    DELETE FROM public.audit_logs;
    DELETE FROM public.notifications;
    DELETE FROM public.sessions WHERE user_id <> sa_public_id;
    DELETE FROM public.api_keys;
    DELETE FROM public.report_histories;
    DELETE FROM public.scheduled_reports;
    DELETE FROM public.license_usages;
    DELETE FROM public.licenses;

    -- 6. Remove non-Super Admin application users & tenant organizations
    DELETE FROM public.users WHERE id <> sa_public_id;
    DELETE FROM public.organizations;

    -- 7. Purge non-Super Admin identities from Supabase Auth schema if available
    IF sa_auth_id IS NOT NULL THEN
        DELETE FROM auth.refresh_tokens WHERE user_id <> sa_auth_id::text;
        DELETE FROM auth.sessions WHERE user_id <> sa_auth_id;
        DELETE FROM auth.identities WHERE user_id <> sa_auth_id;
        DELETE FROM auth.users WHERE id <> sa_auth_id;
    END IF;

    RAISE NOTICE 'SUCCESS: Maintenance purge completed. Super Admin (%) preserved.', target_admin_email;
END $$;
