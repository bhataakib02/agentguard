from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any, Dict
import datetime

class RegisterRequest(BaseModel):
    org_name: str
    full_name: str
    email: str
    password: Optional[str] = None
    auth_user_id: Optional[str] = None
    role: Optional[str] = "USER"

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    auth_user_id: Optional[str] = None

class LocalLoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    auth_user_id: Optional[str] = None
    role: str
    full_name: str
    email: str
    org_name: str

class UserSchema(BaseModel):
    id: str
    auth_user_id: Optional[str] = None
    org_id: Optional[str] = None
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    status: str
    created_at: datetime.datetime
    org_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AgentCreateRequest(BaseModel):
    name: str
    department: str = "Operations"
    purpose: str = "Autonomous AI Agent Workflow"
    model_name: str = "gpt-4o"
    model_version: str = "1.0.0"
    environment: str = "PRODUCTION"
    autonomy_level: str = "MEDIUM"
    daily_budget: float = 10000.0
    org_id: Optional[str] = None
    owner_id: Optional[str] = None

class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    purpose: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    environment: Optional[str] = None
    autonomy_level: Optional[str] = None
    daily_budget: Optional[float] = None
    owner_id: Optional[str] = None

class AgentSchema(BaseModel):
    id: str
    agent_code: str
    org_id: str
    owner_id: str
    name: str
    department: str
    purpose: str
    model_name: str
    model_version: str
    environment: str
    autonomy_level: str
    status: str
    risk_score: int
    trust_score: int
    daily_budget: float
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class AgentCredentialCreateRequest(BaseModel):
    name: Optional[str] = None
    credential_type: str = "API_KEY"
    expires_in_days: Optional[int] = None

class AgentCredentialResponse(BaseModel):
    id: str
    agent_id: str
    name: Optional[str] = None
    key_prefix: Optional[str] = None
    credential_type: str
    status: str
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None
    last_used_at: Optional[datetime.datetime] = None
    revoked_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AgentCredentialCreatedResponse(BaseModel):
    credential: AgentCredentialResponse
    plaintext_token: str
    warning: str = "Store this credential securely immediately. It will NEVER be shown again."

class MachineAuthRequest(BaseModel):
    credential: str
    agent_code: Optional[str] = None

class MachineAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    agent_id: str
    agent_code: str
    org_id: str
    autonomy_level: str
    jti: str
    expires_at: str

class PassportVerifyResponse(BaseModel):
    valid: bool
    status: str
    verification_status: str
    agent_code: str
    passport_number: str
    algorithm: str
    key_id: str
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    reason: Optional[str] = None

class AgentRuntimeHeartbeatRequest(BaseModel):
    session_token_jti: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentRuntimeHeartbeatResponse(BaseModel):
    status: str
    agent_code: str
    agent_status: str
    heartbeat_at: datetime.datetime
    session_active: bool

class PermissionCreateRequest(BaseModel):
    agent_id: Optional[str] = None
    resource_type: str  # DATABASE, API, TOOL, FILE, SYSTEM
    resource_name: str  # e.g. payments, orders, refund_tool
    action: str         # READ, WRITE, CREATE, UPDATE, DELETE, EXECUTE, APPROVE, EXPORT, ADMIN
    is_allowed: bool = True

class PermissionSchema(BaseModel):
    id: str
    agent_id: str
    resource_type: str
    resource_name: str
    action: str
    is_allowed: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class RuntimeAuthorizeRequest(BaseModel):
    action: str
    resource: str
    target: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    amount: Optional[float] = 0.0
    capability_token: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    prompt: Optional[str] = None
    agent_id: Optional[str] = None
    agent_code: Optional[str] = None

class RuntimeAuthorizeResponse(BaseModel):
    authorized: bool
    decision: str  # ALLOW, REVIEW, REFUSE
    decision_id: Optional[str] = None
    reason: str
    stage_failed: Optional[str] = None
    agent_code: str
    org_id: str
    action: str
    resource: str
    approval_required: bool = False
    approval_id: Optional[str] = None
    risk_score: int = 0
    policy_name: Optional[str] = None
    execution_gate_token: Optional[str] = None

class CircuitBreakerResetRequest(BaseModel):
    agent_id: str
    reason: Optional[str] = "Manual operator reset"



class CapabilityTokenRequest(BaseModel):
    agent_id: str
    capability_name: str
    scope: str
    amount_limit: float = 0.0
    ttl_seconds: int = 60

class CapabilityTokenValidateRequest(BaseModel):
    token_code: str
    agent_id: Optional[str] = None
    capability_name: Optional[str] = None
    amount: Optional[float] = 0.0
    scope: Optional[str] = None


class CapabilityTokenSchema(BaseModel):
    id: str
    token_code: str
    agent_id: str
    capability_name: str
    scope: str
    amount_limit: float
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    status: str

    model_config = ConfigDict(from_attributes=True)

class ActionEvaluateRequest(BaseModel):
    prompt: str
    agent_id: Optional[str] = None
    amount: float = 0.0

class DecisionSchema(BaseModel):
    id: str
    agent_id: str
    user_id: Optional[str] = None
    intent_summary: str
    action_requested: str
    resource_target: str
    amount: float
    decision: str
    risk_score: int
    policy_name: Optional[str] = None
    explanation: str
    execution_status: str
    timestamp: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class ApprovalActionRequest(BaseModel):
    action: str  # APPROVE, REJECT

class RedTeamRunRequest(BaseModel):
    agent_id: str
    attack_type: str

class DigitalTwinRunRequest(BaseModel):
    agent_id: str
    scenario_type: str

class AssistantQueryRequest(BaseModel):
    question: str

class AssistantQueryResponse(BaseModel):
    question: str
    answer: str
    data: Optional[Any] = None
    recommendations: Optional[List[str]] = None
    provider: Optional[str] = "NOT_CONFIGURED"
    model: Optional[str] = None
    tokens_used: Optional[int] = 0

# --- Policy & Policy Rule Schemas ---

class PolicyRuleCreateRequest(BaseModel):
    condition_expression: str
    decision_output: str = "REVIEW"  # ALLOW, REVIEW, REFUSE
    risk_delta: int = 0
    description: Optional[str] = None

class PolicyRuleUpdateRequest(BaseModel):
    condition_expression: Optional[str] = None
    decision_output: Optional[str] = None
    risk_delta: Optional[int] = None
    description: Optional[str] = None

class PolicyRuleSchema(BaseModel):
    id: str
    policy_id: str
    condition_expression: str
    decision_output: str
    risk_delta: int
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PolicyCreateRequest(BaseModel):
    name: str
    category: str = "GOVERNANCE"
    priority: int = 1
    status: str = "ACTIVE"
    version: str = "1.0.0"
    rules: Optional[List[PolicyRuleCreateRequest]] = None

class PolicyUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    version: Optional[str] = None

class PolicySchema(BaseModel):
    id: str
    org_id: str
    name: str
    category: str
    priority: int
    status: str
    version: str
    created_at: datetime.datetime
    rules: List[PolicyRuleSchema] = []
    rules_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# --- Webhook Schemas ---

class WebhookCreateRequest(BaseModel):
    name: str
    url: str
    event_types: Optional[List[str]] = ["*"]

class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None
    event_types: Optional[List[str]] = None

class WebhookEndpointSchema(BaseModel):
    id: str
    org_id: str
    name: str
    url: str
    secret_preview: Optional[str] = None
    is_active: bool
    event_types: List[str]
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)

class WebhookCreatedResponse(WebhookEndpointSchema):
    secret: str  # Only returned once upon creation!

class WebhookDeliverySchema(BaseModel):
    id: str
    webhook_id: str
    event_type: str
    status: str
    response_code: Optional[int] = None
    attempt_count: int
    error_message: Optional[str] = None
    delivered_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- SIEM Forwarding Schemas ---

class SiemConfigCreateRequest(BaseModel):
    name: Optional[str] = "Primary SIEM Collector"
    provider: Optional[str] = "GENERIC_HTTP"  # GENERIC_HTTP, SPLUNK_HEC, DATADOG
    collector_url: str
    auth_token: Optional[str] = None
    format: Optional[str] = "JSONL"           # JSONL, CEF
    is_active: Optional[bool] = True
    batch_size: Optional[int] = 100

class SiemConfigResponse(BaseModel):
    id: str
    org_id: Optional[str] = None
    name: str
    provider: str
    collector_url: str
    auth_token_preview: Optional[str] = None
    format: str
    is_active: bool
    batch_size: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SiemDeliverySchema(BaseModel):
    id: str
    org_id: str
    batch_id: str
    provider: str
    format: str
    event_count: int
    status: str
    attempt_count: int
    response_code: Optional[int] = None
    error_message: Optional[str] = None
    next_attempt_at: Optional[datetime.datetime] = None
    delivered_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class SiemTriggerForwardRequest(BaseModel):
    format: Optional[str] = None  # None = use configured format
    batch_size: Optional[int] = None

class SiemTriggerForwardResponse(BaseModel):
    status: str
    batch_id: str
    delivery_id: str
    event_count: int
    format: str
    message: str


# --- Notification Schemas ---

class NotificationSchema(BaseModel):
    id: str
    user_id: Optional[str] = None
    type: str
    title: str
    message: str
    severity: str
    is_read: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- Tool Registry Schemas ---

class ToolCreateRequest(BaseModel):
    name: str
    category: str = "API"  # DATABASE, EMAIL, PAYMENT, REFUND, CLOUD, CRM, STORAGE, API
    endpoint: Optional[str] = None
    description: Optional[str] = None
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    schema_definition: Optional[Dict[str, Any]] = None
    headers_json: Optional[Dict[str, str]] = None
    timeout_seconds: int = 30


class ToolUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    endpoint: Optional[str] = None
    description: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None
    schema_definition: Optional[Dict[str, Any]] = None
    headers_json: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = None


class ToolResponse(BaseModel):
    id: str
    org_id: Optional[str] = None
    name: str
    category: str
    endpoint: Optional[str] = None
    description: Optional[str] = None
    risk_level: str
    status: str
    latency_ms: int = 120
    schema_definition: Optional[Dict[str, Any]] = None
    headers_json: Optional[Dict[str, str]] = None
    timeout_seconds: int = 30
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Runtime Execution & Forward Proxy Gateway Schemas ---

class RuntimeExecuteRequest(BaseModel):
    execution_gate_token: str
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    override_endpoint: Optional[str] = None


class RuntimeExecuteResponse(BaseModel):
    success: bool
    status: str  # EXECUTED, GATE_TOKEN_INVALID, GATE_TOKEN_REPLAYED, GATE_TOKEN_EXPIRED, AGENT_MISMATCH, SSRF_BLOCKED, EXECUTION_FAILED
    execution_id: Optional[str] = None
    tool_name: Optional[str] = None
    status_code: Optional[int] = None
    response_data: Optional[Any] = None
    latency_ms: int = 0
    gate_token: str
    error: Optional[str] = None


class RuntimeInvokeRequest(BaseModel):
    agent_id: Optional[str] = None
    agent_code: Optional[str] = None
    action: str
    resource: str
    target: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    amount: float = 0.0
    capability_token: Optional[str] = None
    prompt: Optional[str] = None
    tool_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class RuntimeInvokeResponse(BaseModel):
    authorized: bool
    decision: str  # ALLOW, REVIEW, REFUSE
    decision_id: Optional[str] = None
    reason: Optional[str] = None
    approval_required: bool = False
    approval_id: Optional[str] = None
    risk_score: int = 0
    policy_name: Optional[str] = None
    execution_gate_token: Optional[str] = None
    execution: Optional[RuntimeExecuteResponse] = None


class IntentValidationRequest(BaseModel):
    prompt: Optional[str] = None
    tool_name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    arguments: Optional[Dict[str, Any]] = None
    schema_definition: Optional[Dict[str, Any]] = None


class IntentValidationResponse(BaseModel):
    intent: str
    action: str
    resource: str
    amount: float = 0.0
    customer_id: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    schema_valid: bool = True
    schema_errors: List[str] = []
    is_prompt_injection: bool = False
    injection_confidence: float = 0.0
    injection_threat_level: str = "NONE"
    injection_patterns: List[str] = []


class PIIScanRequest(BaseModel):
    text: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    mode: str = "MASK"  # MASK, PARTIAL_MASK, TOKENIZE, BLOCK


class PIIScanResponse(BaseModel):
    has_pii: bool
    findings_count: int
    findings: List[Dict[str, Any]] = []
    sanitized_text: Optional[str] = None
    sanitized_payload: Optional[Dict[str, Any]] = None
    mode_applied: str


class BehaviorProfileUpdateRequest(BaseModel):
    avg_daily_actions: Optional[int] = None
    normal_operating_hours: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    baseline_spending: Optional[float] = None


class BehaviorProfileResponse(BaseModel):
    agent_id: str
    agent_code: str
    name: str
    avg_daily_actions: int
    normal_operating_hours: str
    allowed_tools: List[str]
    baseline_spending: float


class BehaviorEvaluationResponse(BaseModel):
    agent_id: str
    agent_code: str
    deviation_score: float
    is_anomalous: bool
    anomalies_count: int
    anomalies: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}


class RedTeamFuzzRequest(BaseModel):
    agent_id: str
    intensity: str = "STANDARD"  # LIGHT, STANDARD, AGGRESSIVE
    include_pii_tests: bool = True
    include_injection_tests: bool = True
    include_boundary_tests: bool = True


class RedTeamFuzzResponse(BaseModel):
    agent_id: str
    agent_code: str
    intensity: str
    total_attacks: int
    passed_count: int
    vulnerability_count: int
    resilience_score: float
    test_results: List[Dict[str, Any]] = []
    weakest_areas: List[str] = []
    remediation_plan: List[str] = []


class OutputScanRequest(BaseModel):
    text: str
    grounding_context: Optional[str] = None
    policy_mode: str = "BLOCK"  # BLOCK, REDACT, WARN, ALLOW
    toxicity_threshold: float = 50.0


class OutputScanResponse(BaseModel):
    is_safe: bool
    decision: str  # ALLOW, WARN, REDACT, BLOCK
    reason: str
    toxicity_score: float
    threat_level: str
    categories_detected: List[str] = []
    is_grounded: bool
    hallucination_score: float
    findings: List[Dict[str, Any]] = []
    sanitized_text: Optional[str] = None


class BYOKConfigRequest(BaseModel):
    provider: str  # SYSTEM_MANAGED, AWS_KMS, GCP_KMS, VAULT, LOCAL_AES
    key_arn: Optional[str] = None
    key_alias: Optional[str] = None
    config_params: Optional[Dict[str, Any]] = None


class BYOKConfigResponse(BaseModel):
    org_id: str
    provider: str
    key_arn: Optional[str] = None
    key_alias: Optional[str] = None
    status: str
    is_custom_key: bool


class BYOKTestResponse(BaseModel):
    success: bool
    provider: str
    key_arn: Optional[str] = None
    key_alias: Optional[str] = None
    status: str
    probe_verified: bool = False
    error: Optional[str] = None


class AiModelCreate(BaseModel):
    model_name: str
    provider: str = "OpenAI"
    cost_per_1k_tokens: float = 0.002
    avg_latency_ms: int = 300
    accuracy_rating: float = 0.98
    status: str = "ACTIVE"


class AiModelResponse(BaseModel):
    id: str
    model_name: str
    provider: str
    cost_per_1k_tokens: float
    avg_latency_ms: int
    accuracy_rating: float
    status: str
    provider_configured: bool = False
    health: str = "HEALTHY"

    model_config = ConfigDict(from_attributes=True)


class ModelPricingResponse(BaseModel):
    id: str
    provider: str
    model: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    currency: str = "USD"
    active: bool = True

    model_config = ConfigDict(from_attributes=True)


class ModelSelectRequest(BaseModel):
    task_complexity: str = "HIGH"  # LOW, MEDIUM, HIGH, CRITICAL
    max_latency_ms: Optional[int] = None
    max_cost_per_1k: Optional[float] = None
    preferred_provider: Optional[str] = None


class ModelSelectResponse(BaseModel):
    selected_model: str
    provider: str
    tier: str
    avg_latency_ms: int
    cost_per_1k_tokens: float
    accuracy_rating: float
    recommended_for: str
    selection_reason: str


# --- External Isolated Sandbox Execution Provider Schemas ---

class SandboxExecuteRequest(BaseModel):
    execution_gate_token: str
    tool_name: Optional[str] = "python_sandbox"
    language: str = "python"
    code: str
    stdin: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    network_enabled: Optional[bool] = False
    env_vars: Optional[Dict[str, str]] = None


class SandboxExecuteResponse(BaseModel):
    success: bool
    status: str  # SUCCEEDED, FAILED, TIMED_OUT, CANCELLED, REJECTED, NOT_CONFIGURED, UNAVAILABLE, NOT_AUTHORIZED, GATE_TOKEN_REPLAYED, GATE_TOKEN_INVALID, GATE_TOKEN_EXPIRED, AGENT_MISMATCH
    execution_id: str
    job_id: Optional[str] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration_ms: int = 0
    resource_usage: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[Dict[str, Any]]] = None
    gate_token: str
    cleaned_up: bool = True
    provider: str = "NOT_CONFIGURED"
    isolation_level: str = "NONE"
    error: Optional[str] = None


class SandboxJobResponse(BaseModel):
    id: str
    org_id: str
    agent_id: str
    decision_id: Optional[str] = None
    execution_id: str
    tool_name: str
    language: str
    status: str
    provider: str
    isolation_level: str
    cpu_limit: float
    memory_limit_mb: int
    timeout_seconds: int
    network_isolated: bool
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    resource_usage_json: Optional[Dict[str, Any]] = None
    artifacts_json: Optional[List[Dict[str, Any]]] = None
    cleanup_status: str
    created_at: datetime.datetime
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SandboxStatusResponse(BaseModel):
    configured: bool
    provider: str
    status: str
    endpoint_configured: bool
    resource_limits: Dict[str, Any]
    isolation_technology: str
    supported_languages: List[str]


class SandboxCancelResponse(BaseModel):
    success: bool
    execution_id: str
    status: str
    message: str


# ============================================================================
# PREDICTIVE ACTION CONTROL ENGINE (PACE) SCHEMAS - PHASE 1
# ============================================================================

class ActionControlEvaluationRequest(BaseModel):
    action_type: str
    target_resource: str
    operation: Optional[str] = None
    agent_id: Optional[str] = None
    agent_code: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    amount: Optional[float] = 0.0
    context: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    prompt: Optional[str] = None
    history_window_size: Optional[int] = 10
    history_window_seconds: Optional[int] = 900


class SequencePatternDetection(BaseModel):
    pattern_name: str
    severity: str
    description: str
    risk_delta: int


class SequenceIndicators(BaseModel):
    window_size: int
    window_seconds: int
    events_evaluated: int
    missing_history: bool
    patterns_detected: List[SequencePatternDetection] = []
    sequence_risk_delta: int = 0
    explanation: str
    features: Dict[str, Any] = {}


class ActionControlEvaluationResponse(BaseModel):
    decision: str  # ALLOW, REVIEW, REFUSE
    risk_score: int
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_scale: str = "0-100 (LOW <=30, MEDIUM <=60, HIGH <=80, CRITICAL >80)"
    reason: str
    policy_applied: Optional[str] = None
    policy_id: Optional[str] = None
    rule_id: Optional[str] = None
    risk_breakdown: Optional[Dict[str, Any]] = None
    sequence_indicators: Optional[SequenceIndicators] = None
    approval_required: bool = False
    approval_status: Optional[str] = None  # PENDING, APPROVED, REJECTED, NOT_REQUIRED
    approval_id: Optional[str] = None
    execution_gate_token: Optional[str] = None
    agent_code: str
    org_id: str
    action_type: str
    target_resource: str
    correlation_id: str
    evaluated_at: datetime.datetime


class ActionControlExecuteResponse(BaseModel):
    evaluation: ActionControlEvaluationResponse
    executed: bool
    execution_status: str  # EXECUTED, BLOCKED, PENDING_APPROVAL, EXECUTION_FAILED
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None




