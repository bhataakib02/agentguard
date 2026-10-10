/**
 * Custom Error classes for @agentguard/sdk
 */

import { AuthorizeResponse } from "./types.js";

export class AgentGuardError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AgentGuardError";
  }
}

export class AgentGuardAuthError extends AgentGuardError {
  public statusCode: number;

  constructor(message: string, statusCode = 401) {
    super(message);
    this.name = "AgentGuardAuthError";
    this.statusCode = statusCode;
  }
}

export class AgentGuardGovernanceRefusal extends AgentGuardError {
  public decisionId?: string;
  public riskScore?: number;
  public decisionPayload?: AuthorizeResponse;

  constructor(explanation: string, decisionId?: string, riskScore?: number, decisionPayload?: AuthorizeResponse) {
    super(`AgentGuard Refusal [Decision ${decisionId || "UNKNOWN"}]: ${explanation}`);
    this.name = "AgentGuardGovernanceRefusal";
    this.decisionId = decisionId;
    this.riskScore = riskScore;
    this.decisionPayload = decisionPayload;
  }
}

export class AgentGuardCircuitBreakerError extends AgentGuardError {
  public agentCode?: string;

  constructor(message: string, agentCode?: string) {
    super(message);
    this.name = "AgentGuardCircuitBreakerError";
    this.agentCode = agentCode;
  }
}

export class AgentGuardExecutionError extends AgentGuardError {
  public statusCode: number;

  constructor(message: string, statusCode = 502) {
    super(message);
    this.name = "AgentGuardExecutionError";
    this.statusCode = statusCode;
  }
}
