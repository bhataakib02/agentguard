

const getBaseApiUrl = () => {
  const url = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  return url.replace(/\/+$/, "");
};

export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  try {
    const token = typeof window !== "undefined" ? localStorage.getItem("agentguard_token") : null;
    const orgContext = typeof window !== "undefined" ? localStorage.getItem("agentguard_selected_org_id") : null;
    
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(orgContext ? { "X-Organization-Context": orgContext } : {}),
      ...(options.headers as Record<string, string>),
    };

    const baseUrl = getBaseApiUrl();
    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const res = await fetch(`${baseUrl}${cleanEndpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP Error ${res.status}`);
    }
    return await res.json();
  } catch (err: any) {
    console.error(`API Error on ${endpoint}:`, err);
    if (err?.name === "TypeError" && err?.message === "Failed to fetch") {
      throw new Error("Unable to connect to AgentGuard API server. Please check network connectivity or server status.");
    }
    throw err;
  }
}

/**
 * Production WebSocket client with automatic exponential backoff reconnect and heartbeat ping/pong
 */
export class RobustWebSocketClient {
  private url: string;
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private pingIntervalMs = 15000;
  private pingTimer: any = null;
  private onMessageCallback: ((data: any) => void) | null = null;

  constructor(onMessage?: (data: any) => void) {
    const wsHost = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
    this.url = wsHost;
    this.onMessageCallback = onMessage || null;
  }

  public async connect() {
    if (typeof window === "undefined") return;

    try {
      const token = localStorage.getItem("agentguard_token");
      let authParam = "";
      if (token) {
        try {
          const res = await fetchApi("/auth/ws-ticket", { method: "POST" });
          if (res?.ticket) {
            authParam = `ticket=${encodeURIComponent(res.ticket)}`;
          }
        } catch {
          authParam = `token=${encodeURIComponent(token)}`;
        }
      }
      const separator = this.url.includes("?") ? "&" : "?";
      const connectionUrl = authParam
        ? `${this.url}${separator}${authParam}`
        : this.url;
      this.socket = new WebSocket(connectionUrl);

      this.socket.onopen = () => {
        console.log("WebSocket connection established");
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.socket.onmessage = (event) => {
        try {
          if (event.data === "PONG") return;
          const data = JSON.parse(event.data);
          if (this.onMessageCallback) {
            this.onMessageCallback(data);
          }
        } catch (e) {
          // ignore non-json frames
        }
      };

      this.socket.onclose = () => {
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.socket.onerror = () => {
        this.socket?.close();
      };
    } catch (err) {
      this.scheduleReconnect();
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.pingTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send("PING");
      }
    }, this.pingIntervalMs);
  }

  private stopHeartbeat() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
    console.log(`Scheduling WebSocket reconnect attempt #${this.reconnectAttempts} in ${delay}ms...`);
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  public send(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }

  public disconnect() {
    this.stopHeartbeat();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export interface SandboxStatus {
  provider: string;
  configured: boolean;
  available: boolean;
  healthy: boolean;
  details?: Record<string, any>;
}

export interface SandboxJob {
  job_id: string;
  org_id: string;
  agent_id: string;
  decision_id: string;
  status: string;
  runtime_language: string;
  exit_code?: number | null;
  output?: string | null;
  error?: string | null;
  duration_ms?: number | null;
  memory_used_mb?: number | null;
  created_at: string;
  completed_at?: string | null;
  artifacts_cleaned_up: boolean;
}

export async function getSandboxStatus(): Promise<SandboxStatus> {
  return await fetchApi("/runtime/sandbox/status");
}

export async function executeSandbox(request: {
  execution_token: string;
  runtime_language: string;
  code: string;
  entrypoint?: string;
  stdin?: string;
  timeout_seconds?: number;
  memory_limit_mb?: number;
  allow_network?: boolean;
}): Promise<any> {
  return await fetchApi("/runtime/sandbox/execute", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getSandboxJobs(limit: number = 50, offset: number = 0): Promise<SandboxJob[]> {
  return await fetchApi(`/runtime/sandbox/jobs?limit=${limit}&offset=${offset}`);
}

export async function getSandboxJob(jobId: string): Promise<SandboxJob> {
  return await fetchApi(`/runtime/sandbox/jobs/${jobId}`);
}

export async function cancelSandboxJob(jobId: string): Promise<{ success: boolean; job_id: string; status: string; message: string }> {
  return await fetchApi(`/runtime/sandbox/jobs/${jobId}/cancel`, {
    method: "POST",
  });
}

