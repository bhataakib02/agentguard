/**
 * Custom Error classes for @agentguard/sdk
 */
export class AgentGuardError extends Error {
    constructor(message) {
        super(message);
        this.name = "AgentGuardError";
    }
}
export class AgentGuardAuthError extends AgentGuardError {
    statusCode;
    constructor(message, statusCode = 401) {
        super(message);
        this.name = "AgentGuardAuthError";
        this.statusCode = statusCode;
    }
}
export class AgentGuardGovernanceRefusal extends AgentGuardError {
    decisionId;
    riskScore;
    decisionPayload;
    constructor(explanation, decisionId, riskScore, decisionPayload) {
        super(`AgentGuard Refusal [Decision ${decisionId || "UNKNOWN"}]: ${explanation}`);
        this.name = "AgentGuardGovernanceRefusal";
        this.decisionId = decisionId;
        this.riskScore = riskScore;
        this.decisionPayload = decisionPayload;
    }
}
export class AgentGuardCircuitBreakerError extends AgentGuardError {
    agentCode;
    constructor(message, agentCode) {
        super(message);
        this.name = "AgentGuardCircuitBreakerError";
        this.agentCode = agentCode;
    }
}
export class AgentGuardExecutionError extends AgentGuardError {
    statusCode;
    constructor(message, statusCode = 502) {
        super(message);
        this.name = "AgentGuardExecutionError";
        this.statusCode = statusCode;
    }
}
//# sourceMappingURL=errors.js.map