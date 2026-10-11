/**
 * Type definitions for @agentguard/sdk
 */
export interface AgentGuardConfig {
    agentCode: string;
    agentKey: string;
    baseUrl?: string;
    orgId?: string;
    timeoutMs?: number;
    raiseOnRefusal?: boolean;
}
export interface AuthResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    agent_code: string;
    department?: string;
    autonomy_level?: number;
    passport?: {
        payload: Record<string, any>;
        signature: string;
        algorithm: string;
    };
}
export interface AuthorizeRequest {
    action_requested: string;
    amount?: number;
    target_resource?: string;
    intent_name?: string;
    parameters?: Record<string, any>;
    effective_prompt?: string;
    capability_token?: string;
}
export interface AuthorizeResponse {
    decision_id: string;
    decision: "ALLOW" | "REVIEW" | "REFUSE";
    explanation: string;
    risk_score: number;
    execution_gate_token?: string;
    circuit_breaker_status?: "HEALTHY" | "DEGRADED" | "TRIPPED";
    required_approval?: boolean;
    approval_request_id?: string;
    evaluated_at?: string;
}
export interface ExecuteRequest {
    tool_name: string;
    parameters: Record<string, any>;
    execution_gate_token: string;
    action_intent?: string;
    call_id?: string;
}
export interface ExecuteResponse {
    execution_id: string;
    tool_name: string;
    status: "SUCCESS" | "FAILED";
    output: any;
    duration_ms: number;
    sanitized: boolean;
    provenance_token?: string;
}
export interface InvokeRequest {
    action_requested: string;
    tool_name: string;
    parameters: Record<string, any>;
    amount?: number;
    target_resource?: string;
    effective_prompt?: string;
    capability_token?: string;
}
export interface InvokeResponse {
    decision_id?: string;
    decision: "ALLOW" | "REVIEW" | "REFUSE";
    explanation?: string;
    risk_score?: number;
    execution_id?: string;
    tool_name?: string;
    execution_status?: "SUCCESS" | "FAILED" | "NOT_EXECUTED";
    output?: any;
    duration_ms?: number;
    sanitized?: boolean;
}
export interface HeartbeatResponse {
    status: string;
    agent_code: string;
    session_id: string;
    expires_at: string;
}
export interface ScanPiiRequest {
    text?: string;
    parameters?: Record<string, any>;
    mode?: "MASK" | "PARTIAL_MASK" | "TOKENIZE" | "BLOCK";
}
export interface ScanPiiResponse {
    pii_detected: boolean;
    count: number;
    types_found: string[];
    redacted_text?: string;
    redacted_parameters?: Record<string, any>;
    mode: string;
}
export interface ScanOutputRequest {
    output_text: string;
    reference_context?: string;
    policy_mode?: "ALLOW" | "WARN" | "REDACT" | "BLOCK";
}
export interface ScanOutputResponse {
    blocked: boolean;
    action: "ALLOW" | "WARN" | "REDACT" | "BLOCK";
    sanitized_output: string;
    violations_count: number;
    toxicity_score: number;
    hallucination_score: number;
    findings: string[];
}
//# sourceMappingURL=types.d.ts.map