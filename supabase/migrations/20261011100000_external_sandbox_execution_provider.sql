-- AGENTGUARD Supabase Migration: External Isolated Sandbox Execution Provider
-- Runtime Control Plane for Autonomous AI

CREATE TABLE IF NOT EXISTS sandbox_execution_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE NOT NULL,
    decision_id UUID REFERENCES decisions(id) ON DELETE SET NULL,
    execution_id VARCHAR(100) UNIQUE NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    language VARCHAR(50) DEFAULT 'python' NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
    provider VARCHAR(50) DEFAULT 'NOT_CONFIGURED' NOT NULL,
    isolation_level VARCHAR(50) DEFAULT 'CONTAINER_HARDENED',
    cpu_limit FLOAT DEFAULT 1.0,
    memory_limit_mb INT DEFAULT 512,
    timeout_seconds INT DEFAULT 30,
    network_isolated BOOLEAN DEFAULT TRUE,
    exit_code INT,
    stdout TEXT,
    stderr TEXT,
    error_message TEXT,
    resource_usage_json JSONB DEFAULT '{}'::jsonb,
    artifacts_json JSONB DEFAULT '[]'::jsonb,
    cleanup_status VARCHAR(50) DEFAULT 'CLEANED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_org_id ON sandbox_execution_jobs(org_id);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_agent_id ON sandbox_execution_jobs(agent_id);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_decision_id ON sandbox_execution_jobs(decision_id);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_execution_id ON sandbox_execution_jobs(execution_id);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_status ON sandbox_execution_jobs(status);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_code_hash ON sandbox_execution_jobs(code_hash);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_org_created ON sandbox_execution_jobs(org_id, created_at);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_status_created ON sandbox_execution_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS ix_sandbox_jobs_agent_created ON sandbox_execution_jobs(agent_id, created_at);
