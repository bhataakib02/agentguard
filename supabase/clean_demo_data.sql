-- AGENTGUARD Fail-Safe Supabase PostgreSQL Demo Data Purge Script
-- Run this script in your Supabase Dashboard SQL Editor (https://supabase.com/dashboard/project/xjragvyzlailmtfwjfnm/sql/new)

DO $$
DECLARE
    tbl text;
    tbls text[] := ARRAY[
        'provenance_events',
        'approval_requests',
        'decisions',
        'capability_tokens',
        'permissions',
        'agent_passports',
        'agent_credentials',
        'risk_scores',
        'behavior_profiles',
        'reputation_scores',
        'circuit_breakers',
        'budgets',
        'transactions',
        'security_tests',
        'simulations',
        'resource_usages',
        'anomaly_events',
        'security_incidents',
        'agent_relationships',
        'agents',
        'policy_rules',
        'policies',
        'notifications',
        'sessions',
        'api_keys',
        'users',
        'organizations'
    ];
BEGIN
    FOREACH tbl IN ARRAY tbls LOOP
        BEGIN
            EXECUTE format('DELETE FROM %I;', tbl);
            RAISE NOTICE 'Purged table: %', tbl;
        EXCEPTION WHEN undefined_table THEN
            RAISE NOTICE 'Table % does not exist in schema, safely skipped.', tbl;
        END;
    END LOOP;
END $$;

-- Verification Query (All counts should return 0)
SELECT 
    (SELECT COUNT(*) FROM users) AS remaining_users,
    (SELECT COUNT(*) FROM agents) AS remaining_agents,
    (SELECT COUNT(*) FROM organizations) AS remaining_organizations;
