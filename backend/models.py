import datetime
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
)
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=False))
        else:
            return dialect.type_descriptor(CHAR(36))

def gen_uuid():
    return str(uuid.uuid4())

def is_valid_uuid(val) -> bool:
    if not val:
        return False
    try:
        uuid.UUID(str(val).strip())
        return True
    except (ValueError, AttributeError):
        return False

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=True)
    display_name = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")  # ACTIVE, SUSPENDED, RESTRICTED, DEACTIVATED
    admin_email = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    logo_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Per-tenant custom encryption keys (BYOK)
    kms_provider = Column(String, default="SYSTEM_MANAGED")  # SYSTEM_MANAGED, AWS_KMS, GCP_KMS, VAULT, LOCAL_AES
    kms_key_arn = Column(String, nullable=True)
    kms_key_alias = Column(String, nullable=True)
    kms_key_status = Column(String, default="NOT_CONFIGURED")  # NOT_CONFIGURED, ACTIVE, VERIFYING, DISABLED
    kms_config_json = Column(JSON, default=dict)

    users = relationship("User", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    policies = relationship("Policy", back_populates="organization")
    license = relationship("License", back_populates="organization", uselist=False)
    license_usage = relationship("LicenseUsage", back_populates="organization", uselist=False)
    sandbox_jobs = relationship("SandboxExecutionJob", back_populates="organization", cascade="all, delete-orphan")

    @property
    def plan_id(self):
        return self.license.plan_id if self.license else "FREE"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True)  # FREE, STARTER, PROFESSIONAL, ENTERPRISE
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price_monthly = Column(Float, default=0.0)
    max_users = Column(Integer, default=5)
    max_ai_agents = Column(Integer, default=3)
    max_api_keys = Column(Integer, default=2)
    max_monthly_api_requests = Column(Integer, default=50000)
    max_storage_gb = Column(Float, default=10.0)
    feature_flags = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    licenses = relationship("License", back_populates="plan")


class License(Base):
    __tablename__ = "licenses"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), unique=True, nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    status = Column(String, default="ACTIVE")  # TRIAL, ACTIVE, PAST_DUE, SUSPENDED, EXPIRED, CANCELLED
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    max_users = Column(Integer, default=5)
    max_ai_agents = Column(Integer, default=3)
    max_api_keys = Column(Integer, default=2)
    max_monthly_api_requests = Column(Integer, default=50000)
    max_storage_gb = Column(Float, default=10.0)
    feature_flags = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    @property
    def valid_until(self):
        return self.expiry_date

    @valid_until.setter
    def valid_until(self, val):
        self.expiry_date = val

    organization = relationship("Organization", back_populates="license")
    plan = relationship("Plan", back_populates="licenses")


class LicenseUsage(Base):
    __tablename__ = "license_usages"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), unique=True, nullable=False)
    api_requests_count = Column(Integer, default=0)
    storage_used_gb = Column(Float, default=0.0)
    last_calculated_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="license_usage")


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    auth_user_id = Column(String, unique=True, index=True, nullable=True)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    full_name = Column(String, nullable=False)
    role = Column(String, default="USER")  # ADMIN, MANAGER, SECURITY_OFFICER, AUDITOR, USER, AGENT
    department = Column(String, default="General")
    job_title = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")  # ACTIVE, INACTIVE, SUSPENDED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_login_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    agents = relationship("Agent", back_populates="owner")
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    token = Column(String, index=True, nullable=False)
    refresh_token = Column(String, nullable=True)
    ip_address = Column(String, default="127.0.0.1")
    user_agent = Column(String, default="Browser")
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_code = Column(String, unique=True, index=True, nullable=False)  # e.g., AG-101
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    department = Column(String, default="Operations")
    purpose = Column(Text, nullable=False)
    model_name = Column(String, default="gpt-4o")
    model_version = Column(String, default="1.0.0")
    environment = Column(String, default="PRODUCTION")  # DEVELOPMENT, STAGING, PRODUCTION
    autonomy_level = Column(String, default="MEDIUM")  # LOW, MEDIUM, HIGH, FULL
    status = Column(String, default="NORMAL")  # NORMAL, WARNING, RESTRICTED, HUMAN_APPROVAL, CIRCUIT_BREAK, SUSPENDED
    risk_score = Column(Integer, default=15)
    trust_score = Column(Integer, default=95)
    daily_budget = Column(Float, default=10000.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="agents")
    owner = relationship("User", back_populates="agents")
    passport = relationship("AgentPassport", back_populates="agent", uselist=False)
    credentials = relationship("AgentCredential", back_populates="agent")
    permissions = relationship("Permission", back_populates="agent")
    capability_tokens = relationship("CapabilityToken", back_populates="agent")
    decisions = relationship("Decision", back_populates="agent")
    risk_scores = relationship("RiskScore", back_populates="agent")
    behavior_profile = relationship("BehaviorProfile", back_populates="agent", uselist=False)
    reputation_score = relationship("ReputationScore", back_populates="agent", uselist=False)
    circuit_breaker = relationship("CircuitBreaker", back_populates="agent", uselist=False)
    budget = relationship("Budget", back_populates="agent", uselist=False)
    sandbox_jobs = relationship("SandboxExecutionJob", back_populates="agent", cascade="all, delete-orphan")


class AgentPassport(Base):
    __tablename__ = "agent_passports"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), unique=True, nullable=False)
    passport_number = Column(String, unique=True, nullable=False)
    algorithm = Column(String, default="Ed25519")
    key_id = Column(String, default="agentguard-root-1")
    passport_version = Column(String, default="1.0")
    claims = Column(JSON, nullable=True)
    digital_signature = Column(String, nullable=False)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    verification_status = Column(String, default="VERIFIED")  # VERIFIED, UNVERIFIED, EXPIRED, REVOKED

    agent = relationship("Agent", back_populates="passport")


class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    name = Column(String, nullable=True)
    key_prefix = Column(String, nullable=True)
    credential_type = Column(String, nullable=False)  # API_KEY, OAUTH_TOKEN, PRIVATE_KEY
    key_hash = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE, EXPIRED, REVOKED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="credentials")


class AgentRuntimeSession(Base):
    __tablename__ = "agent_runtime_sessions"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    session_token_jti = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE, CLOSED, EXPIRED, TERMINATED
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_heartbeat_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    agent = relationship("Agent")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    resource_type = Column(String, nullable=False)  # DATABASE, API, TOOL, FILE, SYSTEM
    resource_name = Column(String, nullable=False)
    action = Column(String, nullable=False)  # READ, WRITE, CREATE, UPDATE, DELETE, EXECUTE, APPROVE, EXPORT, ADMIN
    is_allowed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    agent = relationship("Agent", back_populates="permissions")


class Tool(Base):
    __tablename__ = "tools"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, default="API")  # DATABASE, EMAIL, PAYMENT, REFUND, CLOUD, CRM, STORAGE
    endpoint = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    risk_level = Column(String, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String, default="ACTIVE")
    latency_ms = Column(Integer, default=120)
    schema_definition = Column(JSON, default=dict)  # OpenAPI / JSON Schema definition of inputs
    headers_json = Column(JSON, default=dict)  # Custom headers or auth config
    timeout_seconds = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Capability(Base):
    __tablename__ = "capabilities"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, nullable=False)  # e.g. refund:create
    resource = Column(String, nullable=False)
    action = Column(String, nullable=False)
    default_ttl_seconds = Column(Integer, default=60)
    max_amount = Column(Float, default=5000.0)


class CapabilityToken(Base):
    __tablename__ = "capability_tokens"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    token_code = Column(String, unique=True, index=True, nullable=False)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    capability_name = Column(String, nullable=False)
    scope = Column(String, nullable=False)  # e.g. customer=9281
    amount_limit = Column(Float, default=0.0)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE, EXPIRED, REVOKED, USED

    agent = relationship("Agent", back_populates="capability_tokens")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="FINANCE")  # DATA, FINANCE, SECURITY, PRIVACY, TOOLS, AUTONOMY, AGENT_TO_AGENT, RESOURCE
    priority = Column(Integer, default=1)
    status = Column(String, default="ACTIVE")
    version = Column(String, default="1.0.0")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="policies")
    rules = relationship("PolicyRule", back_populates="policy")


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    policy_id = Column(GUID(), ForeignKey("policies.id"), nullable=False)
    condition_expression = Column(String, nullable=False)  # e.g. "amount > 5000"
    decision_output = Column(String, nullable=False)  # ALLOW, REVIEW, REFUSE
    risk_delta = Column(Integer, default=20)
    description = Column(String, nullable=True)

    policy = relationship("Policy", back_populates="rules")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    intent_summary = Column(String, nullable=False)
    action_requested = Column(String, nullable=False)
    resource_target = Column(String, nullable=False)
    amount = Column(Float, default=0.0)
    decision = Column(String, nullable=False)  # ALLOW, REVIEW, REFUSE
    risk_score = Column(Integer, default=15)
    policy_name = Column(String, nullable=True)
    explanation = Column(Text, nullable=False)
    execution_status = Column(String, default="EXECUTED")  # EXECUTED, BLOCKED, PENDING_APPROVAL
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    execution_gate_token = Column(String, nullable=True, index=True)
    gate_token_used = Column(Boolean, default=False)
    executed_at = Column(DateTime, nullable=True)
    tool_id = Column(GUID(), ForeignKey("tools.id"), nullable=True)
    execution_parameters = Column(JSON, default=dict)

    agent = relationship("Agent", back_populates="decisions")
    approval_request = relationship("ApprovalRequest", back_populates="decision", uselist=False, cascade="all, delete-orphan")
    provenance_events = relationship("ProvenanceEvent", back_populates="decision", cascade="all, delete-orphan")
    sandbox_job = relationship("SandboxExecutionJob", back_populates="decision", uselist=False)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    decision_id = Column(GUID(), ForeignKey("decisions.id"), nullable=False)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    approver_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    amount = Column(Float, default=0.0)
    reason = Column(String, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED, EXPIRED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    decision = relationship("Decision", back_populates="approval_request")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    overall_score = Column(Integer, default=15)
    identity_risk = Column(Integer, default=0)
    permission_risk = Column(Integer, default=5)
    behavior_risk = Column(Integer, default=5)
    financial_risk = Column(Integer, default=5)
    data_sensitivity_risk = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    agent = relationship("Agent", back_populates="risk_scores")


class BehaviorProfile(Base):
    __tablename__ = "behavior_profiles"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), unique=True, nullable=False)
    avg_daily_actions = Column(Integer, default=150)
    normal_operating_hours = Column(String, default="09:00 - 18:00")
    allowed_tools_json = Column(JSON, default=list)
    baseline_spending = Column(Float, default=2500.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    agent = relationship("Agent", back_populates="behavior_profile")


class ReputationScore(Base):
    __tablename__ = "reputation_scores"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), unique=True, nullable=False)
    trust_score = Column(Integer, default=95)
    successful_tasks = Column(Integer, default=1240)
    violations_count = Column(Integer, default=0)
    anomalies_count = Column(Integer, default=1)
    overrides_count = Column(Integer, default=2)

    agent = relationship("Agent", back_populates="reputation_score")


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    anomaly_type = Column(String, nullable=False)
    severity = Column(String, default="MEDIUM")
    description = Column(String, nullable=False)
    deviation_score = Column(Float, default=2.5)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class SecurityIncident(Base):
    __tablename__ = "security_incidents"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False, index=True)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    status = Column(String, default="OPEN")    # OPEN, INVESTIGATING, CONTAINED, RESOLVED, CLOSED
    source = Column(String, default="SYSTEM")  # SYSTEM, POLICY_ENGINE, CIRCUIT_BREAKER, ANOMALY_DETECTOR, AUDIT, MANUAL
    affected_user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    assigned_to_user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    timeline_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class CircuitBreaker(Base):
    __tablename__ = "circuit_breakers"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), unique=True, nullable=False)
    state = Column(String, default="NORMAL")
    trigger_reason = Column(String, nullable=True)
    tripped_at = Column(DateTime, nullable=True)
    restored_at = Column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="circuit_breaker")


class ProvenanceEvent(Base):
    __tablename__ = "provenance_events"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    decision_id = Column(GUID(), ForeignKey("decisions.id"), nullable=False)
    human_initiator_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    delegated_agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=True)
    tool_used = Column(String, nullable=True)
    data_accessed = Column(String, nullable=True)
    causal_chain_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    decision = relationship("Decision", back_populates="provenance_events")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    actor_type = Column(String, default="AGENT")  # USER, AGENT, SYSTEM, API_KEY
    actor_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    result = Column(String, nullable=False)  # SUCCESS, DENIED, FAILED, BLOCKED
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AgentRelationship(Base):
    __tablename__ = "agent_relationships"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    parent_agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    child_agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    trust_status = Column(String, default="VERIFIED")
    allowed_delegation_types = Column(String, default="READ,EXECUTE")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False, index=True)
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    key_prefix = Column(String, nullable=False, index=True)  # e.g. "ag_live_1234"
    key_hash = Column(String, nullable=False, unique=True, index=True)  # SHA-256 of raw secret
    scopes = Column(String, default="read,write")
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class UserInvitation(Base):
    """Secure, cryptographic, one-time-use tenant user invitation."""
    __tablename__ = "user_invitations"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    role = Column(String, default="USER", nullable=False)
    invited_by_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)  # SHA-256 hash of random invite token
    status = Column(String, default="PENDING", nullable=False)  # PENDING, ACCEPTED, EXPIRED, REVOKED
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)


class AiModel(Base):
    __tablename__ = "ai_models"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    model_name = Column(String, unique=True, nullable=False)
    provider = Column(String, default="OpenAI")
    cost_per_1k_tokens = Column(Float, default=0.002)
    avg_latency_ms = Column(Integer, default=350)
    accuracy_rating = Column(Float, default=0.98)
    status = Column(String, default="ACTIVE")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), unique=True, nullable=False)
    daily_limit = Column(Float, default=5000.0)
    monthly_limit = Column(Float, default=100000.0)
    current_daily_spend = Column(Float, default=0.0)
    current_monthly_spend = Column(Float, default=0.0)
    currency = Column(String, default="INR")

    agent = relationship("Agent", back_populates="budget")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    amount = Column(Float, nullable=False)
    vendor = Column(String, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, default="APPROVED")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class SecurityTest(Base):
    __tablename__ = "security_tests"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    test_type = Column(String, nullable=False)
    attack_payload = Column(Text, nullable=False)
    defense_result = Column(String, default="PASSED")
    security_score = Column(Integer, default=92)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    scenario_type = Column(String, nullable=False)
    readiness_score = Column(Integer, default=88)
    metrics_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class ResourceUsage(Base):
    __tablename__ = "resource_usages"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    cpu_pct = Column(Float, default=12.5)
    gpu_pct = Column(Float, default=0.0)
    memory_mb = Column(Float, default=512.0)
    compute_cost = Column(Float, default=0.04)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    type = Column(String, default="ALERT")
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    severity = Column(String, default="INFO")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def read(self) -> bool:
        return bool(self.is_read)

    @read.setter
    def read(self, val: bool):
        self.is_read = bool(val)


class ReportHistory(Base):
    __tablename__ = "report_histories"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    report_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    file_format = Column(String, nullable=False)  # PDF, EXCEL, CSV, TEXT
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    filters_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    report_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    file_format = Column(String, default="PDF")
    frequency = Column(String, default="WEEKLY")  # DAILY, WEEKLY, MONTHLY
    recipient_emails = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret_hash = Column(String, nullable=False)  # SHA256 hashed secret for verification
    secret_preview = Column(String, nullable=True)  # Masked preview e.g. "whsec_****12ab"
    secret_key = Column(String, nullable=True)  # Securely stored signing key
    is_active = Column(Boolean, default=True)
    event_types = Column(JSON, default=list)  # ["*"] or specific events
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    organization = relationship("Organization")
    deliveries = relationship("WebhookDelivery", back_populates="endpoint", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    webhook_id = Column(GUID(), ForeignKey("webhook_endpoints.id"), nullable=False)
    event_type = Column(String, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, DELIVERING, DELIVERED, SUCCESS, RETRYING, FAILED, DEAD_LETTER
    response_code = Column(Integer, nullable=True)
    attempt_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    payload_json = Column(JSON, default=dict)
    response_body_preview = Column(String(500), nullable=True)  # First 500 chars of response for debugging
    next_attempt_at = Column(DateTime, nullable=True)            # Scheduled retry time
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")

    __table_args__ = (
        Index("ix_webhook_delivery_status_next", "status", "next_attempt_at"),
    )


# ============================================================================
# PHASE 4: Runtime Telemetry, Cost Governance & Risk Signals
# ============================================================================

class AgentExecution(Base):
    """Tracks individual agent execution/invocation events with token/cost telemetry."""
    __tablename__ = "agent_executions"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    request_id = Column(String, nullable=True, index=True)          # correlation ID
    execution_id = Column(String, nullable=False, index=True)       # unique execution trace
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    action = Column(String, nullable=True)                          # intent / action
    resource = Column(String, nullable=True)                        # target resource
    outcome = Column(String, nullable=False, default="EXECUTED")    # EXECUTED, BLOCKED, PENDING_APPROVAL, ERROR
    risk_score = Column(Integer, default=0)
    policy_decision = Column(String, nullable=True)                 # ALLOW, REVIEW, REFUSE
    policy_id = Column(GUID(), nullable=True)
    policy_rule_id = Column(GUID(), nullable=True)
    decision_id = Column(GUID(), ForeignKey("decisions.id"), nullable=True)
    input_token_count = Column(Integer, default=0)
    output_token_count = Column(Integer, default=0)
    total_token_count = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    provider = Column(String, nullable=True)                        # OpenAI, Anthropic, Google, etc.
    model_name = Column(String, nullable=True)
    latency_ms = Column(Integer, default=0)
    status = Column(String, default="COMPLETED")                    # COMPLETED, ERROR, TIMEOUT
    error_code = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)                      # safe non-sensitive metadata

    __table_args__ = (
        Index("ix_agent_executions_org_ts", "org_id", "timestamp"),
        Index("ix_agent_executions_agent_ts", "agent_id", "timestamp"),
    )


class ModelPricing(Base):
    """Configurable pricing for AI model providers. Used for deterministic cost calculation."""
    __tablename__ = "model_pricing"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    provider = Column(String, nullable=False)                       # e.g. "openai", "anthropic", "google"
    model = Column(String, nullable=False)                          # e.g. "gpt-4o", "claude-3-opus"
    input_cost_per_1k = Column(Float, nullable=False, default=0.0)  # cost per 1000 input tokens
    output_cost_per_1k = Column(Float, nullable=False, default=0.0) # cost per 1000 output tokens
    currency = Column(String, default="USD")
    effective_from = Column(DateTime, default=datetime.datetime.utcnow)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_model_pricing_provider_model", "provider", "model"),
    )


class AgentBudgetConfig(Base):
    """Configurable budget limits and thresholds for agent/org cost governance."""
    __tablename__ = "agent_budget_configs"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=True)  # NULL = org-level default
    daily_token_limit = Column(Integer, nullable=True)
    monthly_token_limit = Column(Integer, nullable=True)
    daily_cost_limit = Column(Float, nullable=True)
    monthly_cost_limit = Column(Float, nullable=True)
    execution_count_limit = Column(Integer, nullable=True)           # daily execution cap
    warning_threshold_pct = Column(Float, default=80.0)              # 80% → WARNING
    exceeded_threshold_pct = Column(Float, default=100.0)            # 100% → EXCEEDED
    auto_suspend_on_exceeded = Column(Boolean, default=False)        # optionally suspend agent
    budget_state = Column(String, default="NORMAL")                  # NORMAL, WARNING, EXCEEDED, SUSPENDED
    current_daily_tokens = Column(Integer, default=0)
    current_monthly_tokens = Column(Integer, default=0)
    current_daily_cost = Column(Float, default=0.0)
    current_monthly_cost = Column(Float, default=0.0)
    current_daily_executions = Column(Integer, default=0)
    last_reset_daily = Column(DateTime, default=datetime.datetime.utcnow)
    last_reset_monthly = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_budget_config_org_agent", "org_id", "agent_id"),
    )


class RuntimeRiskSignal(Base):
    """Deterministic runtime risk signals derived from telemetry and policy decisions."""
    __tablename__ = "runtime_risk_signals"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=True)
    signal_type = Column(String, nullable=False)                    # REPEATED_REFUSALS, HIGH_RISK_VOLUME, BUDGET_EXCEEDED, etc.
    severity = Column(String, default="MEDIUM")                     # LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    evidence_json = Column(JSON, default=dict)                      # factual data backing the signal
    status = Column(String, default="ACTIVE")                       # ACTIVE, ACKNOWLEDGED, RESOLVED, DISMISSED
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(GUID(), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_risk_signals_org_ts", "org_id", "timestamp"),
        Index("ix_risk_signals_agent_ts", "agent_id", "timestamp"),
        Index("ix_risk_signals_status", "status"),
    )


# ============================================================================
# PHASE 6E: Asynchronous Enterprise SIEM Event Forwarding Pipeline
# ============================================================================

class SiemCollectorConfig(Base):
    """
    Persistent configuration for external SIEM log collectors.
    Can be configured per tenant (org_id set) or platform-wide (org_id is NULL).
    Secret authentication credentials are never returned in cleartext to callers.
    """
    __tablename__ = "siem_configs"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, default="Primary SIEM Collector")
    provider = Column(String, default="GENERIC_HTTP")  # GENERIC_HTTP, SPLUNK_HEC, DATADOG
    collector_url = Column(String, nullable=False)
    auth_token_encrypted = Column(String, nullable=True)  # Securely stored authentication credential
    auth_token_preview = Column(String, nullable=True)    # Masked preview e.g. "sec_****ab12"
    format = Column(String, default="JSONL")              # JSONL, CEF
    is_active = Column(Boolean, default=True)
    batch_size = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    organization = relationship("Organization")


class SiemDelivery(Base):
    """
    Tracks asynchronous batch forwarding lifecycle for immutable audit events to external SIEMs.
    Enforces at-least-once delivery, worker claim locks, bounded retries, and sanitized audit trails.
    """
    __tablename__ = "siem_deliveries"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, unique=True, index=True)
    provider = Column(String, nullable=False)             # GENERIC_HTTP, SPLUNK_HEC, DATADOG
    format = Column(String, default="JSONL")              # JSONL, CEF
    event_count = Column(Integer, default=0)
    status = Column(String, default="PENDING", index=True)  # PENDING, CLAIMED, DELIVERING, DELIVERED, RETRYING, DEAD_LETTER
    attempt_count = Column(Integer, default=0)
    response_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)           # Sanitized error details (never raw secrets)
    start_event_id = Column(String, nullable=True)
    end_event_id = Column(String, nullable=True)
    lock_token = Column(String, nullable=True)            # Distributed worker lock identifier
    locked_at = Column(DateTime, nullable=True)
    next_attempt_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    organization = relationship("Organization")

    __table_args__ = (
        Index("ix_siem_deliveries_status_next", "status", "next_attempt_at"),
        Index("ix_siem_deliveries_org_created", "org_id", "created_at"),
    )


# ============================================================================
# PHASE 7: External Isolated Sandbox Execution Provider
# ============================================================================

class SandboxExecutionJob(Base):
    """
    Durable execution lifecycle tracking for untrusted code execution in an isolated sandbox.
    Enforces strict tenant scoping, resource boundaries, stdout/stderr capture,
    ephemeral workspace cleanup, and immutable provenance tracking.
    """
    __tablename__ = "sandbox_execution_jobs"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False, index=True)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False, index=True)
    decision_id = Column(GUID(), ForeignKey("decisions.id"), nullable=True, index=True)
    execution_id = Column(String, unique=True, index=True, nullable=False)
    tool_name = Column(String, nullable=False)
    language = Column(String, default="python", nullable=False)
    code_hash = Column(String, index=True, nullable=False)  # SHA-256 hash of executed code
    status = Column(String, default="PENDING", index=True)  # PENDING, QUEUED, RUNNING, SUCCEEDED, FAILED, TIMED_OUT, CANCELLED, REJECTED, NOT_CONFIGURED, UNAVAILABLE
    provider = Column(String, default="NOT_CONFIGURED")     # NOT_CONFIGURED, REMOTE_WORKER, GVISOR, FIRECRACKER, MOCK_TEST_WORKER
    isolation_level = Column(String, default="CONTAINER_HARDENED")
    cpu_limit = Column(Float, default=1.0)
    memory_limit_mb = Column(Integer, default=512)
    timeout_seconds = Column(Integer, default=30)
    network_isolated = Column(Boolean, default=True)
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    resource_usage_json = Column(JSON, default=dict)        # cpu_time_ms, peak_memory_mb, duration_ms
    artifacts_json = Column(JSON, default=list)             # output files, hashes, sizes
    cleanup_status = Column(String, default="CLEANED")      # CLEANED, PENDING, FAILED
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="sandbox_jobs")
    agent = relationship("Agent", back_populates="sandbox_jobs")
    decision = relationship("Decision", back_populates="sandbox_job")

    __table_args__ = (
        Index("ix_sandbox_jobs_org_created", "org_id", "created_at"),
        Index("ix_sandbox_jobs_status_created", "status", "created_at"),
        Index("ix_sandbox_jobs_agent_created", "agent_id", "created_at"),
    )




