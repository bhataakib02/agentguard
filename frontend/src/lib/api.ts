const getBaseApiUrl = () => {
  if (typeof window !== "undefined") {
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL;
    }
  }
  return "http://localhost:8000/api";
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
    const res = await fetch(`${baseUrl}${endpoint}`, {
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

  public connect() {
    if (typeof window === "undefined") return;

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        console.log("WebSocket connection established:", this.url);
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

