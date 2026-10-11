-- AGENTGUARD Supabase Migration: Asynchronous Enterprise SIEM Event Forwarding Pipeline
-- Runtime Control Plane for Autonomous AI

CREATE TABLE IF NOT EXISTS siem_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) DEFAULT 'Primary SIEM Collector',
    provider VARCHAR(50) DEFAULT 'GENERIC_HTTP',
    collector_url VARCHAR(500) NOT NULL,
    auth_token_encrypted VARCHAR(500),
    auth_token_preview VARCHAR(50),
    format VARCHAR(20) DEFAULT 'JSONL',
    is_active BOOLEAN DEFAULT TRUE,
    batch_size INT DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS siem_deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    batch_id VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    format VARCHAR(20) DEFAULT 'JSONL',
    event_count INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'PENDING',
    attempt_count INT DEFAULT 0,
    response_code INT,
    error_message TEXT,
    start_event_id VARCHAR(100),
    end_event_id VARCHAR(100),
    lock_token VARCHAR(100),
    locked_at TIMESTAMP WITH TIME ZONE,
    next_attempt_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_siem_deliveries_org_id ON siem_deliveries(org_id);
CREATE INDEX IF NOT EXISTS ix_siem_deliveries_status ON siem_deliveries(status);
CREATE INDEX IF NOT EXISTS ix_siem_deliveries_status_next ON siem_deliveries(status, next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_siem_deliveries_org_created ON siem_deliveries(org_id, created_at);
