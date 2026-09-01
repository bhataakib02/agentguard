-- AGENTGUARD Complete Database Reset & Clean Production Data Script
-- Preserves Super Admin (thefreelancer2076@gmail.com) and Platform Metadata
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/xjragvyzlailmtfwjfnm/sql/new

DO $$
DECLARE
    sa_auth_id UUID;
    sa_public_id UUID;
BEGIN
    -- 1. SAFETY CHECK: Resolve Super Admin from auth.users
    SELECT id INTO sa_auth_id FROM auth.users WHERE email = 'thefreelancer2076@gmail.com';
    IF sa_auth_id IS NULL THEN
        RAISE EXCEPTION 'SAFETY ABORT: Super Admin account (thefreelancer2076@gmail.com) not found in auth.users!';
    END IF;

    -- 2. SAFETY CHECK: Resolve Super Admin from public.users
    SELECT id INTO sa_public_id FROM public.users WHERE email = 'thefreelancer2076@gmail.com';
    IF sa_public_id IS NULL THEN
        RAISE EXCEPTION 'SAFETY ABORT: Super Admin account (thefreelancer2076@gmail.com) not found in public.users!';
    END IF;

    RAISE NOTICE 'Super Admin Verified. Auth ID: %, Public ID: %', sa_auth_id, sa_public_id;

    -- 3. Detach Super Admin from tenant organization and explicitly ensure SUPER_ADMIN role & ACTIVE status
    UPDATE public.users 
    SET org_id = NULL, 
        role = 'SUPER_ADMIN', 
        status = 'ACTIVE' 
    WHERE email = 'thefreelancer2076@gmail.com';

    -- 4. Purge all tenant data in foreign-key safe order
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
    DELETE FROM public.sessions;
    DELETE FROM public.api_keys;
    DELETE FROM public.report_histories;
    DELETE FROM public.scheduled_reports;
    DELETE FROM public.license_usages;
    DELETE FROM public.licenses;

    -- 5. Remove non-Super Admin application users & tenant organizations
    DELETE FROM public.users WHERE email <> 'thefreelancer2076@gmail.com';
    DELETE FROM public.organizations;

    -- 6. Purge non-Super Admin accounts from Supabase Auth schema
    DELETE FROM auth.refresh_tokens;
    DELETE FROM auth.sessions;
    DELETE FROM auth.identities WHERE user_id <> sa_auth_id;
    DELETE FROM auth.users WHERE id <> sa_auth_id;

    RAISE NOTICE 'SUCCESS: Database successfully purged of all tenant data. Super Admin preserved.';
END $$;
