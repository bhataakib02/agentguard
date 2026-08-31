-- AGENTGUARD Complete Supabase PostgreSQL Schema Migration
-- Runtime Control Plane for Autonomous AI

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. ORGANIZATIONS
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_user_id VARCHAR(255) UNIQUE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'MANAGER',
    department VARCHAR(100) DEFAULT 'General',
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    refresh_token TEXT,
    ip_address VARCHAR(45) DEFAULT '127.0.0.1',
    user_agent TEXT DEFAULT 'Browser',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. AGENTS
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_code VARCHAR(50) UNIQUE NOT NULL,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    owner_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(100) DEFAULT 'Operations',
    purpose TEXT NOT NULL,
    model_name VARCHAR(100) DEFAULT 'gpt-4o',
    model_version VARCHAR(50) DEFAULT '1.0.0',
    environment VARCHAR(50) DEFAULT 'PRODUCTION',
    autonomy_level VARCHAR(50) DEFAULT 'MEDIUM',
    status VARCHAR(50) DEFAULT 'NORMAL',
    risk_score INT DEFAULT 15,
    trust_score INT DEFAULT 95,
    daily_budget NUMERIC(12,2) DEFAULT 10000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- 5. AGENT PASSPORTS
CREATE TABLE IF NOT EXISTS agent_passports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
    passport_number VARCHAR(100) UNIQUE NOT NULL,
    digital_signature TEXT NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verification_status VARCHAR(50) DEFAULT 'VERIFIED'
);

-- 6. PERMISSIONS
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    resource_type VARCHAR(100) NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    is_allowed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. CAPABILITY TOKENS
CREATE TABLE IF NOT EXISTS capability_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_code VARCHAR(100) UNIQUE NOT NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    capability_name VARCHAR(100) NOT NULL,
    scope VARCHAR(255) NOT NULL,
    amount_limit NUMERIC(12,2) DEFAULT 0.00,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE'
);

-- 8. POLICIES
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) DEFAULT 'FINANCE',
    priority INT DEFAULT 1,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    version VARCHAR(50) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. DECISIONS
CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    intent_summary TEXT NOT NULL,
    action_requested VARCHAR(100) NOT NULL,
    resource_target VARCHAR(255) NOT NULL,
    amount NUMERIC(12,2) DEFAULT 0.00,
    decision VARCHAR(50) NOT NULL,
    risk_score INT DEFAULT 15,
    policy_name VARCHAR(255),
    explanation TEXT NOT NULL,
    execution_status VARCHAR(50) DEFAULT 'EXECUTED',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 10. APPROVAL REQUESTS
CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID REFERENCES decisions(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    approver_id UUID REFERENCES users(id) ON DELETE SET NULL,
    amount NUMERIC(12,2) DEFAULT 0.00,
    reason TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 11. AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    actor_type VARCHAR(50) DEFAULT 'AGENT',
    actor_id VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    result VARCHAR(50) NOT NULL,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 12. CIRCUIT BREAKERS
CREATE TABLE IF NOT EXISTS circuit_breakers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
    state VARCHAR(50) DEFAULT 'NORMAL',
    trigger_reason TEXT,
    tripped_at TIMESTAMP WITH TIME ZONE,
    restored_at TIMESTAMP WITH TIME ZONE
);

-- ROW LEVEL SECURITY (RLS) POLICIES
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_passports ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE capability_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read agents" ON agents FOR SELECT USING (true);
CREATE POLICY "Allow public read decisions" ON decisions FOR SELECT USING (true);
CREATE POLICY "Allow public read audit_logs" ON audit_logs FOR SELECT USING (true);
CREATE POLICY "Allow public read organizations" ON organizations FOR SELECT USING (true);
CREATE POLICY "Allow public read users" ON users FOR SELECT USING (true);
