-- AGENTGUARD Canonical Plans Seed Migration
-- Ensures canonical subscription tiers (FREE, STARTER, PROFESSIONAL, ENTERPRISE) exist idempotently

CREATE TABLE IF NOT EXISTS plans (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    price_monthly FLOAT DEFAULT 0.0,
    max_users INT DEFAULT 5,
    max_ai_agents INT DEFAULT 3,
    max_api_keys INT DEFAULT 2,
    max_monthly_api_requests INT DEFAULT 50000,
    max_storage_gb FLOAT DEFAULT 10.0,
    feature_flags JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO plans (id, name, description, price_monthly, max_users, max_ai_agents, max_api_keys, max_monthly_api_requests, max_storage_gb, feature_flags, created_at)
VALUES
('FREE', 'Free Community', 'Basic community plan for evaluation', 0.0, 3, 2, 1, 10000, 5.0, '{}'::jsonb, NOW()),
('STARTER', 'Starter Plan', 'Small team AI agent governance & oversight', 299.0, 10, 5, 5, 100000, 20.0, '{}'::jsonb, NOW()),
('PROFESSIONAL', 'Professional Enterprise', 'Advanced enterprise AI governance, SOC & red-team lab', 999.0, 50, 25, 20, 1000000, 100.0, '{}'::jsonb, NOW()),
('ENTERPRISE', 'Custom Enterprise', 'Full-scale multi-tenant enterprise control plane with dedicated SLA', 4999.0, 1000, 500, 100, 10000000, 1000.0, '{}'::jsonb, NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price_monthly = EXCLUDED.price_monthly,
    max_users = EXCLUDED.max_users,
    max_ai_agents = EXCLUDED.max_ai_agents,
    max_api_keys = EXCLUDED.max_api_keys,
    max_monthly_api_requests = EXCLUDED.max_monthly_api_requests,
    max_storage_gb = EXCLUDED.max_storage_gb;
