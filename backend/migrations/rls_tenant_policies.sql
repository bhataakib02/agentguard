-- AGENTGUARD Multi-Tenant PostgreSQL Row Level Security (RLS) Policy Migration
-- Enables RLS across all tenant-scoped database tables

-- 1. Organizations Table RLS
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_organizations ON organizations
    FOR ALL
    USING (
        id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
    );

-- 2. Users Table RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_users ON users
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
    );

-- 3. Agents Table RLS
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_agents ON agents
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
    );

-- 4. Licenses Table RLS
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_licenses ON licenses
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
    );

-- 5. Audit Logs Table RLS
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    FOR ALL
    USING (
        actor_id IN (SELECT id::text FROM users WHERE org_id::text = current_setting('app.current_org_id', true))
        OR current_setting('app.current_user_role', true) = 'SUPER_ADMIN'
    );
