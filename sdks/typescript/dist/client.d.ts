/**
 * AgentGuardClient for TypeScript / Node.js
 */
import { AgentGuardConfig, AuthResponse, AuthorizeRequest, AuthorizeResponse, ExecuteRequest, ExecuteResponse, InvokeRequest, InvokeResponse, HeartbeatResponse, ScanPiiRequest, ScanPiiResponse, ScanOutputRequest, ScanOutputResponse } from "./types.js";
export declare class AgentGuardClient {
    private agentCode;
    private agentKey;
    private baseUrl;
    private orgId?;
    private timeoutMs;
    private raiseOnRefusal;
    private sessionToken?;
    passport?: Record<string, any>;
    constructor(config: AgentGuardConfig);
    private getHeaders;
    /**
     * Authenticates agent machine credentials against POST /api/runtime/auth.
     */
    authenticate(): Promise<AuthResponse>;
    /**
     * Evaluates action against the 15-stage AgentGuard Runtime Kernel.
     */
    authorize(req: AuthorizeRequest): Promise<AuthorizeResponse>;
    /**
     * Executes approved tool call through Egress Tool Proxy Gateway.
     */
    execute(req: ExecuteRequest): Promise<ExecuteResponse>;
    /**
     * Unified pre-flight check + execution via POST /api/runtime/invoke.
     */
    invoke(req: InvokeRequest): Promise<InvokeResponse>;
    /**
     * Sends heartbeat ping via POST /api/runtime/heartbeat.
     */
    heartbeat(): Promise<HeartbeatResponse>;
    /**
     * Scans text or parameters for sensitive PII.
     */
    scanPii(req: ScanPiiRequest): Promise<ScanPiiResponse>;
    /**
     * Scans agent output or LLM responses for toxicity, hate speech, dangerous instructions,
     * and ungrounded hallucinations against reference context.
     */
    scanOutput(req: ScanOutputRequest): Promise<ScanOutputResponse>;
}
//# sourceMappingURL=client.d.ts.map