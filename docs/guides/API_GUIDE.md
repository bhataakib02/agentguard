# REST & WebSocket API Guide

This guide provides a reference for the **AGENTGUARD** REST and WebSocket APIs.

---

## 1. Authentication & Security Headers

All API endpoints (except public health checks and login) require valid authentication. AGENTGUARD supports two authentication methods:

1. **Bearer JWT Token:** Used by human users and management applications.
   ```http
   Authorization: Bearer <jwt_access_token>
   ```
2. **API Key:** Used by SDK clients and autonomous machine agents.
   ```http
   X-API-Key: ag_live_pk_<32_hex_chars>
   ```

---

## 2. Core API Endpoints

### 2.1 Predictive Action Control Engine (PACE)

The core runtime evaluation gateway:

- **Endpoint:** `POST /api/evaluate`
- **Authentication:** Required (API Key or Bearer Token)
- **Request Payload:**
  ```json
  {
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "action": "execute_query",
    "target_resource": "finance.payroll_records",
    "parameters": {
      "query": "SELECT employee_id, salary FROM payroll",
      "limit": 100
    },
    "context": {
      "session_id": "sess-9988",
      "environment": "production"
    }
  }
  ```
- **Response Payload (Decision: ALLOW):**
  ```json
  {
    "decision_id": "dec-7711-uuid",
    "outcome": "ALLOW",
    "risk_score": 0.12,
    "confidence": 0.98,
    "reasons": ["Action conforms to standard read-only financial query policy."],
    "capability_token": "cap_token_signed_sha256_hash",
    "evaluated_at": "2026-10-16T22:30:00Z"
  }
  ```
- **Response Payload (Decision: REVIEW - Escalation Required):**
  ```json
  {
    "decision_id": "dec-7712-uuid",
    "outcome": "REVIEW",
    "risk_score": 0.74,
    "confidence": 0.91,
    "reasons": ["Target resource classified as RESTRICTED_PII.", "Requires Security Officer approval."],
    "escalation_id": "esc-4401-uuid",
    "evaluated_at": "2026-10-16T22:30:00Z"
  }
  ```
- **Response Payload (Decision: REFUSE - Interception):**
  ```json
  {
    "decision_id": "dec-7713-uuid",
    "outcome": "REFUSE",
    "risk_score": 0.96,
    "confidence": 0.99,
    "reasons": ["Potential SQL injection or unauthorized schema modification detected."],
    "blocked": true,
    "evaluated_at": "2026-10-16T22:30:00Z"
  }
  ```

---

### 2.2 Agent Management

- **List Organization Agents:** `GET /api/agents`
- **Register New Agent:** `POST /api/agents`
  ```json
  {
    "name": "CustomerSupport-Agent-01",
    "description": "Autonomous customer support triage agent",
    "model_id": "gpt-4o",
    "framework": "langchain"
  }
  ```
- **Retrieve Agent Passport:** `GET /api/agents/{agent_id}`
- **Update Agent Status (Quarantine / Active):** `PATCH /api/agents/{agent_id}/status`
  ```json
  {
    "status": "SUSPENDED",
    "reason": "Anomalous token consumption observed."
  }
  ```

---

### 2.3 Policy Catalog & Governance

- **List Active Policies:** `GET /api/policies`
- **Create Policy Rule:** `POST /api/policies`
  ```json
  {
    "name": "Block Shell Command Execution",
    "description": "Prohibits agents from executing bash commands on host systems",
    "action_pattern": "execute_shell|run_bash",
    "enforcement_mode": "STRICT_REFUSE",
    "severity": "CRITICAL"
  }
  ```

---

### 2.4 Audit & Provenance

- **Query Audit Events:** `GET /api/audit`
- **Filter Parameters:** `agent_id`, `outcome`, `start_time`, `end_time`, `limit`, `offset`.
- **Response:** Paginated list of immutable events including cryptographic SHA-256 hash chains (`previous_hash`, `record_hash`).

---

### 2.5 Platform Operator APIs (`SUPER_ADMIN` Only)

These endpoints require authentic `SUPER_ADMIN` platform privileges:

- **Global Security Posture:** `GET /api/platform/security`
  - Returns real aggregated incident counts, blocked execution totals, and quarantined identities across all tenant organizations.
- **Platform Overview:** `GET /api/platform/overview`
  - Returns tenant counts, active agents, license distributions, and system health status.
- **Tenant Provisioning:** `POST /api/platform/organizations`
- **License Management:** `POST /api/platform/licenses/{org_id}/extend`

---

## 3. Real-Time Telemetry via WebSocket

AGENTGUARD provides a secure WebSocket gateway for real-time risk alerts and live decision telemetry:

- **Endpoint:** `ws://<host>:<port>/ws` (or `wss://` in production)
- **Authentication:** Token passed via initial handshake query parameter or WebSocket message:
  ```json
  {
    "type": "AUTH",
    "token": "<jwt_access_token>"
  }
  ```
- **Real-Time Event Stream Example:**
  ```json
  {
    "event": "PACE_DECISION_EVALUATED",
    "timestamp": "2026-10-16T22:31:00Z",
    "agent_id": "a1b2c3d4-...",
    "action": "database_write",
    "outcome": "REFUSE",
    "risk_score": 0.92
  }
  ```
