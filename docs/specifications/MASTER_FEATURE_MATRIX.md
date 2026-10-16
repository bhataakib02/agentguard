# Master Feature & Capability Matrix

**Classification:** Comprehensive Platform Capability Matrix  
**Architecture:** AGENTGUARD Enterprise AI Control Plane  

---

## 1. Runtime Governance & Policy Control

| Feature | Description | Support Status |
| :--- | :--- | :---: |
| **Predictive Action Control Engine (PACE)** | Real-time evaluation kernel enforcing `ALLOW`, `REVIEW`, and `REFUSE` outcomes | Production Ready |
| **Deterministic Policy Rule Matching** | Exact regex, parameter boundary, and resource name matching | Production Ready |
| **Semantic Threat & Prompt Injection Detection** | Heuristic evaluation of instructions targeting safety boundary bypass | Production Ready |
| **Dynamic Capability Tokens** | Cryptographically signed, single-use execution tokens | Production Ready |
| **Tool Execution Proxy Gateway** | Controlled downstream tool dispatch requiring capability token proof | Production Ready |

---

## 2. Security, IAM & Identity

| Feature | Description | Support Status |
| :--- | :--- | :---: |
| **Five-Role Organizational IAM** | Full support for `ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT` | Production Ready |
| **Global Platform Operator Model** | Dedicated `SUPER_ADMIN` tier for cross-tenant health and licensing | Production Ready |
| **Cryptographic Agent Passports** | Unique agent identity verification with framework bindings | Production Ready |
| **Emergency Agent Quarantine** | Instant kill-switch disabling compromised agents | Production Ready |
| **Immediate Token Revocation** | Redis-backed token invalidation and secret rotation | Production Ready |

---

## 3. Observability, Audit & Compliance

| Feature | Description | Support Status |
| :--- | :--- | :---: |
| **Immutable Audit Log** | Append-only audit trail recording every agent action and administrative decision | Production Ready |
| **SHA-256 Provenance Hash-Chaining** | Cryptographic proof linking records to detect tampering | Production Ready |
| **Compliance Framework Mapping** | Automated mapping to SOC 2, ISO 42001, NIST AI RMF, EU AI Act | Production Ready |
| **Automated Report Generation** | Scheduled and on-demand exports in PDF, CSV, and XLSX formats | Production Ready |
| **Real-Time WebSocket Telemetry** | Low-latency event streaming for alerts and live dashboard monitoring | Production Ready |

---

## 4. Evaluation, Benchmarking & SDKs

| Feature | Description | Support Status |
| :--- | :--- | :---: |
| **Python SDK (`agentguard`)** | Native Python client with LangChain and CrewAI integration middleware | Production Ready |
| **TypeScript SDK (`@agentguard/sdk`)** | Native Node.js/TypeScript client with full type declarations | Production Ready |
| **Persistent Evaluation Datasets** | PostgreSQL-backed benchmark datasets with versioning and scoring | Production Ready |
| **Digital Twin Simulation** | Sandboxed simulation workbench for offline stress testing | Production Ready |
| **Multi-Tenant Quota Enforcement** | Subscription plan enforcement (Free, Starter, Growth, Enterprise) | Production Ready |
