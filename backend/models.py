import datetime
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
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

    users = relationship("User", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    policies = relationship("Policy", back_populates="organization")
    license = relationship("License", back_populates="organization", uselist=False)
    license_usage = relationship("LicenseUsage", back_populates="organization", uselist=False)


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


class AgentPassport(Base):
    __tablename__ = "agent_passports"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), unique=True, nullable=False)
    passport_number = Column(String, unique=True, nullable=False)
    digital_signature = Column(String, nullable=False)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    verification_status = Column(String, default="VERIFIED")  # VERIFIED, UNVERIFIED, EXPIRED, REVOKED

    agent = relationship("Agent", back_populates="passport")


class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    credential_type = Column(String, nullable=False)  # API_KEY, OAUTH_TOKEN, PRIVATE_KEY
    key_hash = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE, EXPIRED, REVOKED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="credentials")


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
    name = Column(String, nullable=False)
    category = Column(String, default="API")  # DATABASE, EMAIL, PAYMENT, REFUND, CLOUD, CRM, STORAGE
    endpoint = Column(String, nullable=True)
    risk_level = Column(String, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String, default="ACTIVE")
    latency_ms = Column(Integer, default=120)


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

    agent = relationship("Agent", back_populates="decisions")
    approval_request = relationship("ApprovalRequest", back_populates="decision", uselist=False, cascade="all, delete-orphan")
    provenance_events = relationship("ProvenanceEvent", back_populates="decision", cascade="all, delete-orphan")


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
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=True)
    title = Column(String, nullable=False)
    severity = Column(String, default="HIGH")
    status = Column(String, default="OPEN")
    timeline_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


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
    event_type = Column(String, nullable=False)
    actor_type = Column(String, default="AGENT")
    actor_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    result = Column(String, nullable=False)
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


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
    org_id = Column(GUID(), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    scopes = Column(String, default="read,write")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


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
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


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
