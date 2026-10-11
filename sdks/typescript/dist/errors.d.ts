/**
 * Custom Error classes for @agentguard/sdk
 */
import { AuthorizeResponse } from "./types.js";
export declare class AgentGuardError extends Error {
    constructor(message: string);
}
export declare class AgentGuardAuthError extends AgentGuardError {
    statusCode: number;
    constructor(message: string, statusCode?: number);
}
export declare class AgentGuardGovernanceRefusal extends AgentGuardError {
    decisionId?: string;
    riskScore?: number;
    decisionPayload?: AuthorizeResponse;
    constructor(explanation: string, decisionId?: string, riskScore?: number, decisionPayload?: AuthorizeResponse);
}
export declare class AgentGuardCircuitBreakerError extends AgentGuardError {
    agentCode?: string;
    constructor(message: string, agentCode?: string);
}
export declare class AgentGuardExecutionError extends AgentGuardError {
    statusCode: number;
    constructor(message: string, statusCode?: number);
}
//# sourceMappingURL=errors.d.ts.map