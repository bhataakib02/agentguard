-- ============================================================================
-- AGENTGUARD Production Database Schema Reconciliation Bridge
-- Target: Elevates legacy Supabase schema (16 tables) to full canonical parity (49 tables)
-- Non-destructive: Uses CREATE TABLE IF NOT EXISTS and ADD COLUMN IF NOT EXISTS
-- Preserves all existing tenant data, users, organizations, and credentials
-- ============================================================================

BEGIN;

-- 1. Ensure required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Add missing columns to pre-existing tables
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS slug VARCHAR;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS display_name VARCHAR;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'ACTIVE';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS admin_email VARCHAR;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_url VARCHAR;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_path VARCHAR;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS kms_provider VARCHAR DEFAULT 'SYSTEM_MANAGED';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS kms_key_arn VARCHAR;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS kms_key_alias VARCHAR;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS kms_key_status VARCHAR DEFAULT 'NOT_CONFIGURED';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS kms_config_json JSONB DEFAULT '{}'::jsonb;

ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE decisions ADD COLUMN IF NOT EXISTS authorized_endpoint VARCHAR;
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS execution_gate_token VARCHAR(255);
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS gate_token_used BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS executed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS tool_id UUID REFERENCES tools(id) ON DELETE SET NULL;
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS execution_parameters JSONB DEFAULT '{}'::jsonb;

ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

ALTER TABLE agent_passports ADD COLUMN IF NOT EXISTS algorithm VARCHAR DEFAULT 'Ed25519';
ALTER TABLE agent_passports ADD COLUMN IF NOT EXISTS key_id VARCHAR DEFAULT 'agentguard-root-1';
ALTER TABLE agent_passports ADD COLUMN IF NOT EXISTS passport_version VARCHAR DEFAULT '1.0';
ALTER TABLE agent_passports ADD COLUMN IF NOT EXISTS claims JSONB DEFAULT '{}'::jsonb;

-- 3. Create the 33 additional canonical application tables
-- Table: ai_models
CREATE TABLE IF NOT EXISTS ai_models (
	id UUID NOT NULL, 
	model_name VARCHAR NOT NULL, 
	provider VARCHAR, 
	cost_per_1k_tokens FLOAT, 
	avg_latency_ms INTEGER, 
	accuracy_rating FLOAT, 
	status VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (model_name)
);

-- Table: capabilities
CREATE TABLE IF NOT EXISTS capabilities (
	id UUID NOT NULL, 
	name VARCHAR NOT NULL, 
	resource VARCHAR NOT NULL, 
	action VARCHAR NOT NULL, 
	default_ttl_seconds INTEGER, 
	max_amount FLOAT, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- Table: model_pricing
CREATE TABLE IF NOT EXISTS model_pricing (
	id UUID NOT NULL, 
	provider VARCHAR NOT NULL, 
	model VARCHAR NOT NULL, 
	input_cost_per_1k FLOAT NOT NULL, 
	output_cost_per_1k FLOAT NOT NULL, 
	currency VARCHAR, 
	effective_from TIMESTAMP WITHOUT TIME ZONE, 
	active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_model_pricing_provider_model ON model_pricing (provider, model);

-- Table: evaluation_datasets
CREATE TABLE IF NOT EXISTS evaluation_datasets (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	provenance VARCHAR(100) NOT NULL, 
	records_count INTEGER NOT NULL, 
	tags JSON, 
	metadata_json JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_evaluation_datasets_org_name UNIQUE (org_id, name), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);
CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_org_id ON evaluation_datasets (org_id);
CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_created_at ON evaluation_datasets (created_at);
CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_org_name ON evaluation_datasets (org_id, name);
CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_org_created ON evaluation_datasets (org_id, created_at);

-- Table: license_usages
CREATE TABLE IF NOT EXISTS license_usages (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	api_requests_count INTEGER, 
	storage_used_gb FLOAT, 
	last_calculated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (org_id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);

-- Table: licenses
CREATE TABLE IF NOT EXISTS licenses (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	plan_id VARCHAR NOT NULL, 
	status VARCHAR, 
	start_date TIMESTAMP WITHOUT TIME ZONE, 
	expiry_date TIMESTAMP WITHOUT TIME ZONE, 
	max_users INTEGER, 
	max_ai_agents INTEGER, 
	max_api_keys INTEGER, 
	max_monthly_api_requests INTEGER, 
	max_storage_gb FLOAT, 
	feature_flags JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (org_id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(plan_id) REFERENCES plans (id)
);

-- Table: tools
CREATE TABLE IF NOT EXISTS tools (
	id UUID NOT NULL, 
	org_id UUID, 
	name VARCHAR NOT NULL, 
	category VARCHAR, 
	endpoint VARCHAR, 
	description TEXT, 
	risk_level VARCHAR, 
	status VARCHAR, 
	latency_ms INTEGER, 
	schema_definition JSON, 
	headers_json JSON, 
	timeout_seconds INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);
CREATE INDEX IF NOT EXISTS ix_tools_name ON tools (name);

-- Table: webhook_endpoints
CREATE TABLE IF NOT EXISTS webhook_endpoints (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	name VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	secret_hash VARCHAR NOT NULL, 
	secret_preview VARCHAR, 
	secret_key VARCHAR, 
	is_active BOOLEAN, 
	event_types JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);

-- Table: api_keys
CREATE TABLE IF NOT EXISTS api_keys (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	owner_id UUID, 
	name VARCHAR NOT NULL, 
	key_prefix VARCHAR NOT NULL, 
	key_hash VARCHAR NOT NULL, 
	scopes VARCHAR, 
	is_revoked BOOLEAN NOT NULL, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE, 
	revoked_by_id UUID, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id), 
	FOREIGN KEY(revoked_by_id) REFERENCES users (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_api_keys_key_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS ix_api_keys_key_prefix ON api_keys (key_prefix);
CREATE INDEX IF NOT EXISTS ix_api_keys_org_id ON api_keys (org_id);

-- Table: evaluation_dataset_records
CREATE TABLE IF NOT EXISTS evaluation_dataset_records (
	id UUID NOT NULL, 
	dataset_id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	record_id VARCHAR(100) NOT NULL, 
	provenance VARCHAR(100) NOT NULL, 
	agent_profile JSON NOT NULL, 
	initial_history JSON, 
	action_sequence JSON NOT NULL, 
	ground_truth_label VARCHAR(50) NOT NULL, 
	ground_truth_notes TEXT, 
	tags JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_eval_record_dataset_record_id UNIQUE (dataset_id, record_id), 
	FOREIGN KEY(dataset_id) REFERENCES evaluation_datasets (id) ON DELETE CASCADE, 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);
CREATE INDEX IF NOT EXISTS ix_evaluation_dataset_records_dataset_id ON evaluation_dataset_records (dataset_id);
CREATE INDEX IF NOT EXISTS ix_evaluation_dataset_records_created_at ON evaluation_dataset_records (created_at);
CREATE INDEX IF NOT EXISTS ix_evaluation_dataset_records_org_id ON evaluation_dataset_records (org_id);
CREATE INDEX IF NOT EXISTS ix_eval_records_org_label ON evaluation_dataset_records (org_id, ground_truth_label);
CREATE INDEX IF NOT EXISTS ix_eval_records_dataset_record ON evaluation_dataset_records (dataset_id, record_id);

-- Table: notifications
CREATE TABLE IF NOT EXISTS notifications (
	id UUID NOT NULL, 
	user_id UUID, 
	type VARCHAR, 
	title VARCHAR NOT NULL, 
	message VARCHAR NOT NULL, 
	severity VARCHAR, 
	is_read BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table: policy_rules
CREATE TABLE IF NOT EXISTS policy_rules (
	id UUID NOT NULL, 
	policy_id UUID NOT NULL, 
	condition_expression VARCHAR NOT NULL, 
	decision_output VARCHAR NOT NULL, 
	risk_delta INTEGER, 
	description VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(policy_id) REFERENCES policies (id)
);

-- Table: report_histories
CREATE TABLE IF NOT EXISTS report_histories (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	report_type VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	file_format VARCHAR NOT NULL, 
	file_path VARCHAR NOT NULL, 
	file_size_bytes INTEGER, 
	filters_json JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table: scheduled_reports
CREATE TABLE IF NOT EXISTS scheduled_reports (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	report_type VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	file_format VARCHAR, 
	frequency VARCHAR, 
	recipient_emails VARCHAR NOT NULL, 
	status VARCHAR, 
	last_run_at TIMESTAMP WITHOUT TIME ZONE, 
	next_run_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table: user_invitations
CREATE TABLE IF NOT EXISTS user_invitations (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	email VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	invited_by_id UUID NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	accepted_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(invited_by_id) REFERENCES users (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_invitations_token_hash ON user_invitations (token_hash);
CREATE INDEX IF NOT EXISTS ix_user_invitations_email ON user_invitations (email);
CREATE INDEX IF NOT EXISTS ix_user_invitations_org_id ON user_invitations (org_id);

-- Table: webhook_deliveries
CREATE TABLE IF NOT EXISTS webhook_deliveries (
	id UUID NOT NULL, 
	webhook_id UUID NOT NULL, 
	event_type VARCHAR NOT NULL, 
	status VARCHAR, 
	response_code INTEGER, 
	attempt_count INTEGER, 
	error_message TEXT, 
	payload_json JSON, 
	response_body_preview VARCHAR(500), 
	next_attempt_at TIMESTAMP WITHOUT TIME ZONE, 
	delivered_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(webhook_id) REFERENCES webhook_endpoints (id)
);
CREATE INDEX IF NOT EXISTS ix_webhook_delivery_status_next ON webhook_deliveries (status, next_attempt_at);

-- Table: agent_budget_configs
CREATE TABLE IF NOT EXISTS agent_budget_configs (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	agent_id UUID, 
	daily_token_limit INTEGER, 
	monthly_token_limit INTEGER, 
	daily_cost_limit FLOAT, 
	monthly_cost_limit FLOAT, 
	execution_count_limit INTEGER, 
	warning_threshold_pct FLOAT, 
	exceeded_threshold_pct FLOAT, 
	auto_suspend_on_exceeded BOOLEAN, 
	budget_state VARCHAR, 
	current_daily_tokens INTEGER, 
	current_monthly_tokens INTEGER, 
	current_daily_cost FLOAT, 
	current_monthly_cost FLOAT, 
	current_daily_executions INTEGER, 
	last_reset_daily TIMESTAMP WITHOUT TIME ZONE, 
	last_reset_monthly TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);
CREATE INDEX IF NOT EXISTS ix_budget_config_org_agent ON agent_budget_configs (org_id, agent_id);

-- Table: agent_credentials
CREATE TABLE IF NOT EXISTS agent_credentials (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	name VARCHAR, 
	key_prefix VARCHAR, 
	credential_type VARCHAR NOT NULL, 
	key_hash VARCHAR NOT NULL, 
	status VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: agent_relationships
CREATE TABLE IF NOT EXISTS agent_relationships (
	id UUID NOT NULL, 
	parent_agent_id UUID NOT NULL, 
	child_agent_id UUID NOT NULL, 
	trust_status VARCHAR, 
	allowed_delegation_types VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_agent_id) REFERENCES agents (id), 
	FOREIGN KEY(child_agent_id) REFERENCES agents (id)
);

-- Table: agent_runtime_sessions
CREATE TABLE IF NOT EXISTS agent_runtime_sessions (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	session_token_jti VARCHAR NOT NULL, 
	status VARCHAR, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	last_heartbeat_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	client_ip VARCHAR, 
	user_agent VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_agent_runtime_sessions_session_token_jti ON agent_runtime_sessions (session_token_jti);

-- Table: anomaly_events
CREATE TABLE IF NOT EXISTS anomaly_events (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	anomaly_type VARCHAR NOT NULL, 
	severity VARCHAR, 
	description VARCHAR NOT NULL, 
	deviation_score FLOAT, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: behavior_profiles
CREATE TABLE IF NOT EXISTS behavior_profiles (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	avg_daily_actions INTEGER, 
	normal_operating_hours VARCHAR, 
	allowed_tools_json JSON, 
	baseline_spending FLOAT, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (agent_id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: budgets
CREATE TABLE IF NOT EXISTS budgets (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	daily_limit FLOAT, 
	monthly_limit FLOAT, 
	current_daily_spend FLOAT, 
	current_monthly_spend FLOAT, 
	currency VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (agent_id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: reputation_scores
CREATE TABLE IF NOT EXISTS reputation_scores (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	trust_score INTEGER, 
	successful_tasks INTEGER, 
	violations_count INTEGER, 
	anomalies_count INTEGER, 
	overrides_count INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (agent_id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: resource_usages
CREATE TABLE IF NOT EXISTS resource_usages (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	cpu_pct FLOAT, 
	gpu_pct FLOAT, 
	memory_mb FLOAT, 
	compute_cost FLOAT, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: risk_scores
CREATE TABLE IF NOT EXISTS risk_scores (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	overall_score INTEGER, 
	identity_risk INTEGER, 
	permission_risk INTEGER, 
	behavior_risk INTEGER, 
	financial_risk INTEGER, 
	data_sensitivity_risk INTEGER, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: runtime_risk_signals
CREATE TABLE IF NOT EXISTS runtime_risk_signals (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	agent_id UUID, 
	signal_type VARCHAR NOT NULL, 
	severity VARCHAR, 
	title VARCHAR NOT NULL, 
	description TEXT, 
	evidence_json JSON, 
	status VARCHAR, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	resolved_by UUID, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);
CREATE INDEX IF NOT EXISTS ix_risk_signals_org_ts ON runtime_risk_signals (org_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_risk_signals_status ON runtime_risk_signals (status);
CREATE INDEX IF NOT EXISTS ix_risk_signals_agent_ts ON runtime_risk_signals (agent_id, timestamp);

-- Table: security_incidents
CREATE TABLE IF NOT EXISTS security_incidents (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	agent_id UUID, 
	title VARCHAR NOT NULL, 
	description TEXT, 
	severity VARCHAR, 
	status VARCHAR, 
	source VARCHAR, 
	affected_user_id UUID, 
	assigned_to_user_id UUID, 
	resolution_notes TEXT, 
	timeline_json JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id), 
	FOREIGN KEY(affected_user_id) REFERENCES users (id), 
	FOREIGN KEY(assigned_to_user_id) REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS ix_security_incidents_org_id ON security_incidents (org_id);

-- Table: security_tests
CREATE TABLE IF NOT EXISTS security_tests (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	test_type VARCHAR NOT NULL, 
	attack_payload TEXT NOT NULL, 
	defense_result VARCHAR, 
	security_score INTEGER, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: simulations
CREATE TABLE IF NOT EXISTS simulations (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	scenario_type VARCHAR NOT NULL, 
	readiness_score INTEGER, 
	metrics_json JSON, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: transactions
CREATE TABLE IF NOT EXISTS transactions (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	amount FLOAT NOT NULL, 
	vendor VARCHAR NOT NULL, 
	currency VARCHAR, 
	status VARCHAR, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

-- Table: agent_executions
CREATE TABLE IF NOT EXISTS agent_executions (
	id UUID NOT NULL, 
	org_id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	request_id VARCHAR, 
	execution_id VARCHAR NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	action VARCHAR, 
	resource VARCHAR, 
	outcome VARCHAR NOT NULL, 
	risk_score INTEGER, 
	policy_decision VARCHAR, 
	policy_id UUID, 
	policy_rule_id UUID, 
	decision_id UUID, 
	input_token_count INTEGER, 
	output_token_count INTEGER, 
	total_token_count INTEGER, 
	estimated_cost FLOAT, 
	provider VARCHAR, 
	model_name VARCHAR, 
	latency_ms INTEGER, 
	status VARCHAR, 
	error_code VARCHAR, 
	metadata_json JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id), 
	FOREIGN KEY(decision_id) REFERENCES decisions (id)
);
CREATE INDEX IF NOT EXISTS ix_agent_executions_agent_ts ON agent_executions (agent_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_agent_executions_execution_id ON agent_executions (execution_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_request_id ON agent_executions (request_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_org_ts ON agent_executions (org_id, timestamp);

-- Table: provenance_events
CREATE TABLE IF NOT EXISTS provenance_events (
	id UUID NOT NULL, 
	decision_id UUID NOT NULL, 
	human_initiator_id UUID, 
	agent_id UUID NOT NULL, 
	delegated_agent_id UUID, 
	tool_used VARCHAR, 
	data_accessed VARCHAR, 
	causal_chain_json JSON, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(decision_id) REFERENCES decisions (id), 
	FOREIGN KEY(human_initiator_id) REFERENCES users (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id), 
	FOREIGN KEY(delegated_agent_id) REFERENCES agents (id)
);

-- 4. Enable Row Level Security (RLS) on newly created tenant tables
ALTER TABLE evaluation_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_dataset_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE license_usages ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE runtime_risk_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_budget_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_histories ENABLE ROW LEVEL SECURITY;

-- 5. Stamp Alembic baseline version so Alembic recognizes the schema
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num)
SELECT '0001_initial_canonical_schema'
WHERE NOT EXISTS (SELECT 1 FROM alembic_version WHERE version_num = '0001_initial_canonical_schema');

COMMIT;
