from pydantic import BaseModel
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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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
