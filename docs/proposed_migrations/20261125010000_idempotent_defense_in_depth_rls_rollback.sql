-- =============================================================================
-- AGENTGUARD DEFENSE-IN-DEPTH POSTGRESQL RLS ROLLBACK SCRIPT
-- Companion to: 20261125010000_idempotent_defense_in_depth_rls.sql
-- Restores database to application-layer-only enforcement if rollback is required.
-- =============================================================================

BEGIN;

DO $$
DECLARE
    r RECORD;
BEGIN
    -- 1. Drop all policies created on public schema tables
    FOR r IN (SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public') LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I;', r.policyname, r.schemaname, r.tablename);
    END LOOP;

    -- 2. Disable Row Level Security on all public schema tables
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY;', r.tablename);
    END LOOP;
END $$;

-- 3. Drop helper functions
DROP FUNCTION IF EXISTS public.current_org_id();
DROP FUNCTION IF EXISTS public.is_super_admin();

COMMIT;
