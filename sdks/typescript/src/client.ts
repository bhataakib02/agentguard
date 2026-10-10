/**
 * AgentGuardClient for TypeScript / Node.js
 */

import {
  AgentGuardConfig,
  AuthResponse,
  AuthorizeRequest,
  AuthorizeResponse,
  ExecuteRequest,
  ExecuteResponse,
  InvokeRequest,
  InvokeResponse,
  HeartbeatResponse,
  ScanPiiRequest,
  ScanPiiResponse,
} from "./types.js";
import {
  AgentGuardError,
  AgentGuardAuthError,
  AgentGuardGovernanceRefusal,
  AgentGuardCircuitBreakerError,
  AgentGuardExecutionError,
} from "./errors.js";

export class AgentGuardClient {
  private agentCode: string;
  private agentKey: string;
  private baseUrl: string;
  private orgId?: string;
  private timeoutMs: number;
  private raiseOnRefusal: boolean;
  private sessionToken?: string;
  public passport?: Record<string, any>;

  constructor(config: AgentGuardConfig) {
    this.agentCode = config.agentCode.trim();
    this.agentKey = config.agentKey.trim();
    this.baseUrl = (config.baseUrl || "http://localhost:8000").replace(/\/$/, "");
    this.orgId = config.orgId;
    this.timeoutMs = config.timeoutMs || 10000;
    this.raiseOnRefusal = config.raiseOnRefusal !== false;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Agent-Code": this.agentCode,
      "X-Agent-Key": this.agentKey,
    };
    if (this.sessionToken) {
      headers["Authorization"] = `Bearer ${this.sessionToken}`;
    }
    if (this.orgId) {
      headers["X-Org-Id"] = this.orgId;
    }
    return headers;
  }

  /**
   * Authenticates agent machine credentials against POST /api/runtime/auth.
   */
  async authenticate(): Promise<AuthResponse> {
    const url = `${this.baseUrl}/api/runtime/auth`;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_code: this.agentCode,
          agent_key: this.agentKey,
        }),
        signal: AbortSignal.timeout(this.timeoutMs),
      });

      if (res.ok) {
        const data = (await res.json()) as AuthResponse;
        this.sessionToken = data.access_token;
        this.passport = data.passport;
        return data;
      }

      const text = await res.text();
      if (res.status === 401 || res.status === 403) {
        throw new AgentGuardAuthError(`Authentication failed: ${text}`, res.status);
      }
      throw new AgentGuardError(`Auth returned status ${res.status}: ${text}`);
    } catch (err: any) {
      if (err instanceof AgentGuardError) throw err;
      throw new AgentGuardError(`Network error during authenticate: ${err.message}`);
    }
  }

  /**
   * Evaluates action against the 15-stage AgentGuard Runtime Kernel.
   */
  async authorize(req: AuthorizeRequest): Promise<AuthorizeResponse> {
    const url = `${this.baseUrl}/api/runtime/authorize`;
    try {
      let res = await fetch(url, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({
          action_requested: req.action_requested,
          amount: req.amount || 0.0,
          target_resource: req.target_resource,
          intent_name: req.intent_name,
          parameters: req.parameters || {},
          effective_prompt: req.effective_prompt,
          capability_token: req.capability_token,
        }),
        signal: AbortSignal.timeout(this.timeoutMs),
      });

      if (res.status === 401 && this.sessionToken) {
        await this.authenticate();
        res = await fetch(url, {
          method: "POST",
          headers: this.getHeaders(),
          body: JSON.stringify(req),
          signal: AbortSignal.timeout(this.timeoutMs),
        });
      }

      if (res.ok) {
        const data = (await res.json()) as AuthorizeResponse;
        if (data.decision === "REFUSE" && this.raiseOnRefusal) {
          throw new AgentGuardGovernanceRefusal(
            data.explanation || "Action refused by policy",
            data.decision_id,
            data.risk_score,
            data
          );
        }
        return data;
      }

      const text = await res.text();
      if (res.status === 403 && text.includes("Circuit breaker")) {
        throw new AgentGuardCircuitBreakerError(text, this.agentCode);
      }
      if (res.status === 401 || res.status === 403) {
        throw new AgentGuardAuthError(`Authorize refused: ${text}`, res.status);
      }
      throw new AgentGuardError(`Authorize returned status ${res.status}: ${text}`);
    } catch (err: any) {
      if (err instanceof AgentGuardError) throw err;
      throw new AgentGuardError(`Network error during authorize: ${err.message}`);
    }
  }

  /**
   * Executes approved tool call through Egress Tool Proxy Gateway.
   */
  async execute(req: ExecuteRequest): Promise<ExecuteResponse> {
    const url = `${this.baseUrl}/api/runtime/execute`;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(req),
        signal: AbortSignal.timeout(this.timeoutMs),
      });

      if (res.ok) {
        return (await res.json()) as ExecuteResponse;
      }

      const text = await res.text();
      throw new AgentGuardExecutionError(`Execute failed: ${text}`, res.status);
    } catch (err: any) {
      if (err instanceof AgentGuardError) throw err;
      throw new AgentGuardError(`Network error during execute: ${err.message}`);
    }
  }

  /**
   * Unified pre-flight check + execution via POST /api/runtime/invoke.
   */
  async invoke(req: InvokeRequest): Promise<InvokeResponse> {
    const url = `${this.baseUrl}/api/runtime/invoke`;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(req),
        signal: AbortSignal.timeout(this.timeoutMs),
      });

      if (res.ok) {
        const data = (await res.json()) as InvokeResponse;
        if (data.decision === "REFUSE" && this.raiseOnRefusal) {
          throw new AgentGuardGovernanceRefusal(
            data.explanation || "Action refused by policy",
            data.decision_id,
            data.risk_score
          );
        }
        return data;
      }

      const text = await res.text();
      throw new AgentGuardError(`Invoke failed: ${text}`);
    } catch (err: any) {
      if (err instanceof AgentGuardError) throw err;
      throw new AgentGuardError(`Network error during invoke: ${err.message}`);
    }
  }

  /**
   * Sends heartbeat ping via POST /api/runtime/heartbeat.
   */
  async heartbeat(): Promise<HeartbeatResponse> {
    const url = `${this.baseUrl}/api/runtime/heartbeat`;
    const res = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      signal: AbortSignal.timeout(this.timeoutMs),
    });
    if (!res.ok) {
      throw new AgentGuardError(`Heartbeat failed: ${await res.text()}`);
    }
    return (await res.json()) as HeartbeatResponse;
  }

  /**
   * Scans text or parameters for sensitive PII.
   */
  async scanPii(req: ScanPiiRequest): Promise<ScanPiiResponse> {
    const url = `${this.baseUrl}/api/runtime/scan-pii`;
    const res = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(this.timeoutMs),
    });
    if (!res.ok) {
      throw new AgentGuardError(`Scan PII failed: ${await res.text()}`);
    }
    return (await res.json()) as ScanPiiResponse;
  }
}
