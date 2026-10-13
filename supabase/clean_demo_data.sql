-- AGENTGUARD Fail-Safe Demo Data Purge Script
-- SAFETY RULES:
-- Requires explicit session variable confirmation prior to execution:
--   SET agentguard.allow_demo_purge = 'CONFIRMED_NON_PRODUCTION';
-- This script will ABORT immediately if executed without this setting.

DO $$
DECLARE
    confirmed_flag text;
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
    BEGIN
        confirmed_flag := current_setting('agentguard.allow_demo_purge', true);
    EXCEPTION WHEN OTHERS THEN
        confirmed_flag := NULL;
    END;

    IF confirmed_flag IS NULL OR confirmed_flag <> 'CONFIRMED_NON_PRODUCTION' THEN
        RAISE EXCEPTION 'SAFETY ABORT: Demo data purge requires explicit non-production confirmation. Execute: SET agentguard.allow_demo_purge = ''CONFIRMED_NON_PRODUCTION'';';
    END IF;

    FOREACH tbl IN ARRAY tbls LOOP
        BEGIN
            EXECUTE format('DELETE FROM %I;', tbl);
            RAISE NOTICE 'Purged table: %', tbl;
        EXCEPTION WHEN undefined_table THEN
            RAISE NOTICE 'Table % does not exist in schema, safely skipped.', tbl;
        END;
    END LOOP;
END $$;

-- Verification Query
SELECT 
    (SELECT COUNT(*) FROM users) AS remaining_users,
    (SELECT COUNT(*) FROM agents) AS remaining_agents,
    (SELECT COUNT(*) FROM organizations) AS remaining_organizations;
