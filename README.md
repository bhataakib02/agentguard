# AGENTGUARD — Runtime Control Plane for Autonomous AI

<p align="center">
  <img src="logo.png" alt="AGENTGUARD Logo" width="180" />
</p>

<p align="center">
  <strong>Non-bypassable pre-flight policy evaluation, sequence-aware risk scoring, cryptographic machine identity, and human-in-the-loop authorization for autonomous AI agents.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-12--Stage_Pre--Flight_Kernel-blue.svg" alt="Architecture" />
  <img src="https://img.shields.io/badge/Backend-FastAPI_%7C_Python_3.10+-009688.svg" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Frontend-Next.js_14_App_Router-black.svg" alt="Next.js" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL_%7C_SQLAlchemy_2.0-336791.svg" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Status-Functional_Control_Plane-green.svg" alt="Status" />
</p>

---

## Table of Contents

- [Overview](#overview)
  - [The Problem: Unconstrained AI Execution](#the-problem-unconstrained-ai-execution)
  - [The AGENTGUARD Approach: The Control Plane Model](#the-agentguard-approach-the-control-plane-model)
  - [Scope: What AGENTGUARD Provides and What It Does Not](#scope-what-agentguard-provides-and-what-it-does-not)
- [Key Features & Implementation Status](#key-features-implementation-status)
- [System Architecture](#system-architecture)
  - [High-Level Architectural Model](#high-level-architectural-model)
  - [Architectural Layers](#architectural-layers)
- [Runtime Decision Lifecycle](#runtime-decision-lifecycle)
  - [The 12-Stage Pre-Flight Interception Gate](#the-12-stage-pre-flight-interception-gate)
  - [Decision Lifecycle Sequence](#decision-lifecycle-sequence)
  - [Execution Gate Tokens & Replay Prevention](#execution-gate-tokens-replay-prevention)
- [The PACE Engine (Predictive Action Control Engine)](#the-pace-engine-predictive-action-control-engine)
  - [Component Architecture](#component-architecture)
  - [Evaluation Inputs & Decision Logic](#evaluation-inputs-decision-logic)
  - [Intervention Levels & Invariants](#intervention-levels-invariants)
  - [Benchmark Evaluation & Metric Interpretation](#benchmark-evaluation-metric-interpretation)
- [Identity, IAM, and Multi-Tenancy](#identity-iam-and-multi-tenancy)
  - [Machine Agent Identity & Cryptographic Passports](#machine-agent-identity-cryptographic-passports)
  - [The 5-Role Enterprise RBAC Model](#the-5-role-enterprise-rbac-model)
  - [Platform Administration vs. Tenant Scoping](#platform-administration-vs-tenant-scoping)
  - [Tenant Isolation Guarantees](#tenant-isolation-guarantees)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation & Local Development](#installation-local-development)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Backend Setup (PowerShell / Windows)](#2-backend-setup-powershell-windows)
  - [3. Frontend Setup](#3-frontend-setup)
  - [4. Bash / Linux / macOS Alternative](#4-bash-linux-macos-alternative)
- [Configuration & Environment Variables](#configuration-environment-variables)
  - [Backend Configuration (`backend/.env`)](#backend-configuration-backendenv)
  - [Frontend Configuration (`frontend/.env.local`)](#frontend-configuration-frontendenvlocal)
- [API Reference & Core Workflows](#api-reference-core-workflows)
  - [API Endpoints Overview](#api-endpoints-overview)
  - [Health & Readiness Probes](#health-readiness-probes)
  - [Pre-Flight Action Evaluation Example](#pre-flight-action-evaluation-example)
  - [Tool Execution Gateway Example](#tool-execution-gateway-example)
- [Software Development Kits (SDKs)](#software-development-kits-sdks)
  - [Python SDK (`sdks/python`)](#python-sdk-sdkspython)
  - [TypeScript SDK (`sdks/typescript`)](#typescript-sdk-sdkstypescript)
- [Simulation, Benchmarks, and Datasets](#simulation-benchmarks-and-datasets)
  - [In-Memory Simulation Lab](#in-memory-simulation-lab)
  - [Persistent Evaluation Datasets](#persistent-evaluation-datasets)
- [Testing & Verification](#testing-verification)
  - [Verified Test Suites](#verified-test-suites)
  - [Verification Checklist](#verification-checklist)
- [Security Model & Responsible Disclosure](#security-model-responsible-disclosure)
- [Deployment Topologies](#deployment-topologies)
  - [Docker Compose Local Deployment](#docker-compose-local-deployment)
  - [Cloud Production Deployment (Render + Vercel)](#cloud-production-deployment-render-vercel)
- [Known Limitations & Current Status](#known-limitations-current-status)
- [Project Roadmap](#project-roadmap)
- [Contributing](#contributing)
- [License & Acknowledgments](#license-acknowledgments)
- [Documentation Index](#documentation-index)

---

## Overview

### The Problem: Unconstrained AI Execution

Modern autonomous AI agents (powered by OpenAI GPT-4o, Anthropic Claude, Google Gemini, or local open-weights LLMs) are increasingly endowed with tool access: SQL execution, financial payment dispatch, cloud infrastructure orchestration, internal API invocation, and shell access.

However, standard enterprise security models fall short when applied to autonomous systems:

1. **Authentication is not intent authorization:** Authenticating an agent (via an API key or bearer token) proves *identity*, but does not ensure the specific proposed action is safe, within budget, aligned with corporate policy, or sequenced correctly.
2. **Context-blind tool execution:** LLMs can be manipulated via direct prompt injection, indirect context contamination, or unexpected tool-calling hallucination to invoke dangerous tools with destructive parameters.
3. **Sequence-level vulnerabilities:** An agent may perform individually benign actions (e.g., `READ table`, `READ secrets`, `EXPORT file`) that cumulatively constitute an exfiltration attack or a policy evasion cascade.
4. **Lack of provable intervention:** Traditional perimeter firewalls cannot parse AI tool payloads, semantic intent, or risk escalation in real-time, resulting in either completely unrestricted execution or brittle, coarse-grained blocking.

### The AGENTGUARD Approach: The Control Plane Model

**AGENTGUARD** acts as a dedicated **Runtime Control Plane** inserted between autonomous AI agents and downstream business resources. It enforces a strict security invariant:

> **Non-Bypassability Invariant:** No autonomous agent may dispatch an external action or execute a business tool without first submitting the proposed action to the control plane, traversing the pre-flight authorization kernel, and obtaining a single-use execution gate token.

```text
┌────────────────┐        1. Propose Action         ┌───────────────────────────────┐
│ Autonomous AI  │ ───────────────────────────────► │          AGENTGUARD           │
│ Agent / SDK    │ ◄─────────────────────────────── │     Runtime Control Plane     │
└────────────────┘   2. ALLOW / REVIEW / REFUSE     └───────────────────────────────┘
        │                                                           │
        │ 3. Dispatch with Gate Token                               │ Persists Decision,
        ▼                                                           │ Risk & Audit Trail
┌────────────────────────────────┐                                  ▼
│   Forward Tool Proxy / API     │ ◄────────────────────── [ Immutable Provenance ]
│ (Databases, Payments, Cloud)   │
└────────────────────────────────┘
```

### Scope: What AGENTGUARD Provides and What It Does Not

To maintain technical precision and set realistic expectations:

* **What AGENTGUARD Provides:**
  * **Pre-flight evaluation kernel:** Validates tenant identity, Ed25519 cryptographic passports, assigned role permissions, dynamic capability tokens, and organizational budget limits.
  * **Deterministic policy enforcement:** Evaluates strict rules (e.g., prohibiting table drops, restricting payment thresholds, blocking cross-tenant data access).
  * **Sequence-aware risk analysis (PACE):** Evaluates rolling action history windows to detect repeated refusal cascades, high-frequency execution bursts, and multi-step reachability paths toward prohibited states.
  * **Three-state decision output:** Produces authoritative `ALLOW`, `REVIEW` (human approval required), or `REFUSE` decisions.
  * **Single-use execution gate tokens:** Cryptographically random, time-bounded (300s TTL) authorization tokens required to execute tools through the proxy gateway.
  * **Human approval escalation:** Centralized queue enabling managers and administrators to inspect, approve, or reject reviewable agent operations.
  * **Operational dashboard & telemetry:** Full-featured Next.js 14 console providing visibility into agents, decisions, real-time WebSocket updates, risk profiles, and audit trails.

* **What AGENTGUARD Does Not Provide:**
  * AGENTGUARD is **not an agent framework** like LangChain, CrewAI, or AutoGen; it is an independent security and governance gateway that integrates into any framework via SDK or REST API.
  * AGENTGUARD does **not autonomously execute arbitrary agent code** inside the control plane process; downstream tool calls are dispatched either through its SSRF-protected Forward Tool Proxy or executed by the client application upon gate token verification.
  * AGENTGUARD does **not replace identity providers**; it integrates with Supabase Auth or standard JWT infrastructure while managing its own database-backed roles, agents, and tenant boundaries.

---

## Key Features & Implementation Status

| Capability | Description | Implementation Status | Authoritative Repository Reference |
| :--- | :--- | :--- | :--- |
| **12-Stage Pre-Flight Kernel** | Validates tenant, passport, credentials, permissions, budget, circuit breaker, policies, and sequence risk. | **Implemented & Tested** | `backend/services/runtime_authorization_service.py` |
| **Three-State Decision Engine** | Evaluates proposed actions into `ALLOW`, `REVIEW`, or `REFUSE` outcomes with deterministic rationale. | **Implemented & Tested** | `backend/routers/decisions.py`, `backend/engines/policy_engine.py` |
| **PACE Engine** | Sequence-aware risk analysis, Markov transition estimation, bounded reachability graph (depth ≤ 4), and minimal-intervention planning. | **Implemented & Tested** | `backend/engines/predictive_action_control_engine.py` |
| **Cryptographic Agent Passports** | Ed25519 asymmetric signature verification for machine agent identities, claims, and lifecycle tracking. | **Implemented & Tested** | `backend/services/passport_service.py`, `models.py:AgentPassport` |
| **Single-Use Execution Gate Tokens** | High-entropy authorization tokens (`gate_<uuid>`) with 300-second TTL and strict replay prevention. | **Implemented & Tested** | `backend/services/tool_proxy_service.py`, `models.py:Decision` |
| **SSRF-Protected Tool Proxy** | Forward egress gateway blocking loopback, link-local, private subnets, and cloud metadata (`169.254.169.254`). | **Implemented & Tested** | `backend/services/tool_proxy_service.py` |
| **Human Approval Workflow** | Operational queue allowing authorized managers to inspect pending actions, review parameters, and issue approvals. | **Implemented & Tested** | `backend/routers/approvals.py`, `models.py:ApprovalRequest` |
| **Five-Role Enterprise IAM** | Role hierarchy (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`) with permission enforcement. | **Implemented & Tested** | `backend/core/permissions.py`, `backend/core/deps.py` |
| **Multi-Tenant Isolation** | Scopes all agents, decisions, policies, and datasets to the caller's tenant organization (`org_id`). | **Implemented & Tested** | `backend/core/deps.py:check_org_isolation` |
| **Real-Time WebSocket Gateway** | WebSocket server (`/ws`) delivering live decisions and approval updates using single-use tickets (`POST /api/v1/auth/ws-ticket`). | **Implemented & Tested** | `backend/ws_manager.py`, `backend/main.py` |
| **Evaluation Datasets & Persistence** | Database-backed ingestion and storage of labeled action-sequence datasets for benchmark validation. | **Implemented & Tested** | `backend/routers/simulation.py`, `models.py:EvaluationDataset` |
| **In-Memory Simulation Lab** | Isolated simulation engine running reproducible comparative evaluations (Baseline vs. PACE) without touching production logs. | **Implemented & Tested** | `backend/engines/simulation_engine.py` |
| **Python SDK** | Synchronous client supporting machine authentication, pre-flight authorization, tool proxy dispatch, and LangChain/CrewAI hooks. | **Implemented & Tested** *(Local)* | `sdks/python/agentguard/client.py` |
| **TypeScript SDK** | Typed client for Node.js / TypeScript supporting runtime authorization, tool dispatch, and guardrail scans. | **Implemented & Tested** *(Local)* | `sdks/typescript/src/client.ts` |
| **Enterprise Dashboard** | Next.js 14 App Router interface with 59 static routes covering governance, agents, decisions, risk, and platform settings. | **Implemented & Tested** | `frontend/src/app` |
| **Celery & Redis Worker Queues** | Asynchronous task execution for scheduled reports and telemetry aggregation; falls back to synchronous eager mode when Redis is absent. | **Implemented & Tested** *(Optional Infra)* | `backend/celery_app.py`, `backend/tasks` |
| **External Isolated Sandboxes** | gVisor / Firecracker / remote worker interface for isolated code execution; defaults to `NOT_CONFIGURED` without dedicated workers. | **Implemented with Limitations** | `backend/services/sandbox_service.py` |

---

## System Architecture

### High-Level Architectural Model

```mermaid
flowchart TD
    subgraph ClientPlane ["Client & AI Agent Environment"]
        Agent[Autonomous AI Agent]
        PySDK[Python SDK / LangChain / CrewAI]
        TsSDK[TypeScript SDK / Node.js]
        WebUI[Next.js 14 Enterprise Dashboard]

        Agent --> PySDK
        Agent --> TsSDK
    end

    subgraph ControlPlane ["AGENTGUARD Control Plane (FastAPI)"]
        Gateway[API Gateway / Ingress Router]
        AuthN[Authentication & IAM Resolver]
        Kernel[12-Stage Pre-Flight Authorization Kernel]
        PACE[PACE Engine: Sequence & Reachability]
        GateGen[Execution Gate Token Generator]
        ApprovalQ[Human Approval Queue]
        Proxy[SSRF-Protected Forward Tool Proxy]

        Gateway --> AuthN
        AuthN --> Kernel
        Kernel --> PACE
        PACE -->|ALLOW| GateGen
        PACE -->|REVIEW| ApprovalQ
        PACE -->|REFUSE| AuditLog
        ApprovalQ -->|Approved by Manager| GateGen
    end

    subgraph DataPlane ["Persistence & Infrastructure"]
        DB[(PostgreSQL / Supabase)]
        Redis[(Redis Message Broker / Cache)]
        CeleryWorkers[Celery Background Workers & Beat]

        Kernel --> DB
        GateGen --> DB
        AuditLog[Immutable Audit Trail] --> DB
        Kernel -. optional .-> Redis
        Redis -. optional .-> CeleryWorkers
    end

    subgraph ExecutionPlane ["Downstream Business Resources"]
        Tools[Databases / Payment Gateways / Cloud APIs]
    end

    PySDK --> Gateway
    TsSDK --> Gateway
    WebUI --> Gateway
    GateGen -->|Single-Use Gate Token| Agent
    Agent -->|Execute Action with Gate Token| Proxy
    Proxy -->|Validated Outbound Call| Tools
```

### Architectural Layers

1. **Ingress & Authentication Layer:**
   * Receives incoming HTTP requests (`/api` and `/api/v1`) and WebSocket connections (`/ws`).
   * Authenticates human users via Supabase JWTs or local API keys (`ag_live_...`).
   * Authenticates AI agents via Machine JWTs or machine credentials (`ag_agent_...`).
   * Authoritatively resolves the caller's tenant organization (`org_id`) and effective role directly from the database.

2. **Pre-Flight Governance Layer:**
   * Houses the 12-stage non-bypassable pre-flight kernel.
   * Executes deterministic policy rules, spending limit checks, cryptographic passport verifications, and agent lifecycle state enforcement.
   * Invokes the PACE engine to detect sequence-level anomalies and reachability hazards.

3. **Human-in-the-Loop Approval Layer:**
   * Catches actions classified as `REVIEW`.
   * Holds execution in an unexecutable pending state and broadcasts real-time alerts via WebSocket to authorized managers.
   * Allows managers or administrators to approve or reject actions. Approving an action generates a single-use execution gate token.

4. **Execution & Egress Boundary:**
   * The Forward Tool Proxy validates single-use execution gate tokens (`gate_<uuid>`), confirms agent ownership, checks 300s expiration, and inspects destination URLs for SSRF vulnerabilities before dispatching HTTP calls.

5. **Persistence & Auditing Layer:**
   * Stores relational entities (Users, Organizations, Agents, Policies, Decisions, Approvals, Datasets, Audit Logs) in PostgreSQL.
   * Enforces foreign-key constraints and ACID transaction semantics.
   * Records immutable audit records for every evaluation, approval, refusal, and execution.

---

## Runtime Decision Lifecycle

### The 12-Stage Pre-Flight Interception Gate

Every proposed action must traverse twelve sequential stages in the runtime authorization kernel (`backend/services/runtime_authorization_service.py`). If any stage fails, the pipeline immediately halts and returns a structured refusal:

```text
 1. Tenant Verification       ──► Verifies tenant organization exists and is ACTIVE.
 2. Agent Lifecycle Status    ──► Checks agent is not SUSPENDED, TERMINATED, or in CIRCUIT_BREAK.
 3. Passport Cryptography     ──► Verifies Ed25519 signature and unexpired passport validity.
 4. Credential Scope          ──► Confirms credential matches agent ID and tenant organization.
 5. Role & Permission Matrix  ──► Verifies agent possesses formal permission for target action.
 6. Capability Tokens         ──► Validates active task-specific capability token if required.
 7. Financial Budget Controls ──► Verifies action amount does not exceed daily remaining allocation.
 8. Sequence-Aware PACE Risk  ──► Inspects rolling history window for refusal cascades and bursts.
 9. Deterministic Policies    ──► Evaluates active policy rules (exact string & regex parameter matching).
10. Reachability Analysis     ──► Checks if action begins a chain toward a prohibited terminal state.
11. Circuit Breaker Invariant ──► Trips agent into CIRCUIT_BREAK if risk or failure thresholds exceed limits.
12. Gate Token Dispatch       ──► If ALLOW, mints a single-use execution gate token with 300s TTL.
```

### Decision Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Agent as Autonomous AI Agent
    participant API as AGENTGUARD API
    participant Kernel as Pre-Flight Kernel
    participant PACE as PACE Engine
    participant DB as PostgreSQL Database
    actor Manager as Human Manager
    participant Tool as Target Tool / External API

    Agent->>API: POST /api/runtime/authorize (action, resource, parameters)
    API->>Kernel: Authorize proposed action
    Kernel->>DB: Fetch agent profile, policies, recent action history
    Kernel->>PACE: Evaluate sequence risk & reachability
    PACE-->>Kernel: Sequence indicators & risk score

    alt Policy or Risk Violation (REFUSE)
        Kernel->>DB: Record Decision (REFUSE) & Audit Incident
        Kernel-->>API: Return Decision: REFUSE (with detailed rationale)
        API-->>Agent: 403 / 200 REFUSE: Action Blocked
    else Sensitive Action / High Risk (REVIEW)
        Kernel->>DB: Record Decision (REVIEW) & Create ApprovalRequest
        Kernel-->>API: Return Decision: REVIEW (approval_id issued)
        API-->>Agent: Action Held Pending Human Review
        API-)Manager: WebSocket / UI Notification: Approval Required
        Manager->>API: POST /api/approvals/{id}/act (APPROVE)
        API->>DB: Update Approval (APPROVED) & Mint Execution Gate Token
    else Safe & Policy-Compliant (ALLOW)
        Kernel->>DB: Record Decision (ALLOW) & Mint Execution Gate Token
        Kernel-->>API: Return Decision: ALLOW (execution_gate_token)
        API-->>Agent: 200 ALLOW + Gate Token (valid for 300s)
    end

    opt Action Execution via Forward Tool Proxy
        Agent->>API: POST /api/runtime/execute (execution_gate_token, tool_name, parameters)
        API->>DB: Verify & Consume Gate Token (atomic single-use mark)
        API->>API: Run SSRF Validation on destination URL
        API->>Tool: Dispatch HTTP request to target tool
        Tool-->>API: Response payload
        API->>DB: Record Telemetry & Provenance Log
        API-->>Agent: Return Tool Execution Output
    end
```

### Execution Gate Tokens & Replay Prevention

When an action is approved (`ALLOW`), AGENTGUARD issues an **Execution Gate Token**:

* **Format:** High-entropy string prefixed with `gate_` (e.g., `gate_7f8a9b2c3d4e5f60`).
* **Storage:** Persisted on the `decisions` table (`models.Decision.execution_gate_token`).
* **Time-to-Live (TTL):** Strictly bounded to **300 seconds (5 minutes)** from creation timestamp.
* **Replay Protection:** Marked atomically upon first consumption (`models.Decision.gate_token_used = True`). Subsequent attempts with the same token are rejected with `400 Bad Request (GATE_TOKEN_REPLAYED)`.
* **Agent Binding:** Cryptographically verified against the calling agent's ID (`decision.agent_id == agent.id`). Re-using a gate token across different agents is blocked with `403 Forbidden (AGENT_MISMATCH)`.

---

## The PACE Engine (Predictive Action Control Engine)

The **Predictive Action Control Engine (PACE)** provides sequence-aware risk assessment, reachability analysis, and minimal-intervention planning.

### Component Architecture

The PACE implementation (`backend/engines/predictive_action_control_engine.py`) consists of four primary components:

1. **`ActionSequenceAnalyzer`:**
   * Examines historical decisions for an agent within its tenant organization over a bounded window (`window_size=10`, `window_seconds=900`).
   * Detects deterministic risk patterns:
     * `REPEATED_REFUSALS_CASCADE`: Triggered when an agent incurs 2 or more consecutive refusals (+20 risk delta).
     * `HIGH_FREQUENCY_BURST`: Triggered when action velocity exceeds 5 actions per 60 seconds (+15 risk delta).
     * `CUMULATIVE_FINANCIAL_SPIKE`: Triggered when cumulative spending across the window exceeds $1,000 (+15 risk delta).
   * Respects operator circuit-breaker resets so historical events prior to restoration do not artificially penalize recovered agents.

2. **`MarkovTransitionEstimator`:**
   * Calculates empirical transition probabilities between observed action states (`current_action:current_resource` $\to$ `next_action:next_resource`).
   * When history is sparse or unobserved, it marks candidates as `transition_type="INFERRED"` and **never fabricates speculative probabilities**.

3. **`ActionChainReachabilityAnalyzer`:**
   * Evaluates whether a proposed action represents an initial step in a sequence that could reach a prohibited terminal state.
   * **Bounded Complexity:** Maximum search depth $\le 4$, maximum explored states $\le 50$.
   * **Prohibited Terminal States:**
     * `UNAUTHORIZED_RESOURCE`: Attempts targeting internal secrets, credential tables, or payment root keys.
     * `RECON_TO_EXFILTRATION`: Reconnaissance actions (`QUERY`, `SELECT`, `SCAN`) followed by exfiltration actions (`EXPORT`, `DUMP`, `DOWNLOAD`).
     * `PRIVILEGE_ESCALATION`: Prohibited administrative privilege modification (`GRANT_ROLE`, `UPDATE_PERMISSIONS`, `SUDO`).
     * `EVASION_POST_REFUSAL`: Destructive database commands following repeated refusals (`DROP_TABLE`, `TRUNCATE_TABLE`, `DISABLE_AUDIT`).
   * **Safe Simulation:** Evaluates reachability *symbolically*; never executes hypothetical candidate actions.

4. **`MinimalInterventionPlanner`:**
   * Selects the least disruptive intervention that satisfies all mandatory security constraints.
   * Invariant: **Mandatory policy prohibitions can never be overridden** by low risk scores, predictive estimates, or optimization routines.

### Evaluation Inputs & Decision Logic

```text
Inputs:
  ├── Agent Identity & Passport Status
  ├── Proposed Action, Resource, & Parameters
  ├── Rolling Action History (Bounded Window: 10 events / 900s)
  └── Active Tenant Policy Catalog

Processing:
  ├── 1. Compute Sequence Risk Delta (Cascades, Bursts, Financial)
  ├── 2. Evaluate Deterministic Policy Rules (String matching, CIDR, Regex)
  ├── 3. Estimate Markov Transitions (Empirical transition frequencies)
  └── 4. Analyze Reachability to Prohibited Terminal States (Graph depth <= 4)

Output:
  ├── Decision: ALLOW | REVIEW | REFUSE
  ├── Sequence Risk Score: 0 - 100
  ├── Intervention Plan: ALLOW_WITHOUT_INTERVENTION | RESTRICT_SCOPE | REQUIRE_APPROVAL | REFUSE_PROHIBITED
  └── Reachability Chains Detected: List of prohibited state paths
```

### Intervention Levels & Invariants

| Disruption Level | Intervention | Enforcement Status | Trigger Condition |
| :---: | :--- | :--- | :--- |
| **0** | `ALLOW_WITHOUT_INTERVENTION` | **Enforced** | No policy violations, risk score $\le 60$, no reachability hazards. |
| **1** | `RESTRICT_SCOPE` | **Recommended** | Moderate sequence risk (score > 60) or high reachability path detected; advises parameter narrowing. |
| **2** | `REQUIRE_APPROVAL` | **Enforced** | Policy mandates supervisory review or critical prohibited terminal state reachable. |
| **3** | `DEFER_ACTION` | **Recommended** | High burst frequency detected; recommends cooling-off delay. |
| **4** | `REFUSE_PROHIBITED` | **Enforced** | Mandatory policy prohibition triggered. Absolute refusal; non-overridable. |

### Benchmark Evaluation & Metric Interpretation

The PACE evaluation engine includes a deterministic synthetic benchmark suite (`backend/engines/pace_evaluator.py`) consisting of 8 representative scenarios probing safe operations, exfiltration sequences, cross-tenant attempts, policy drops, sparse history, novel out-of-distribution verbs, false-positive edges, and cascade evasions.

The evaluator computes standard classification and calibration metrics:

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad \text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

$$\text{Brier Score} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$$

* **Brier Calibration Score:** Measures probability calibration between predicted risk confidence ($p_i$) and true outcomes ($y_i$). Lower values indicate superior probability calibration ($0.0$ represents perfect calibration).
* **Synthetic Benchmark Notice:** Benchmark evaluation results reflect deterministic test suite fixtures and must not be conflated with production operational metrics.

---

## Identity, IAM, and Multi-Tenancy

### Machine Agent Identity & Cryptographic Passports

Autonomous AI employees in AGENTGUARD possess first-class machine identities distinct from human operator accounts:

* **Agent Entity (`models.Agent`):** Defined by a unique `agent_code` (e.g., `AG-FIN-101`), owner ID, tenant organization ID, autonomy level (`LOW`, `MEDIUM`, `HIGH`, `FULL`), daily spending budget, and lifecycle status (`NORMAL`, `WARNING`, `RESTRICTED`, `HUMAN_APPROVAL`, `CIRCUIT_BREAK`, `SUSPENDED`).
* **Cryptographic Passport (`models.AgentPassport`):**
  * Asymmetric digital signature generated using **Ed25519**.
  * Contains verifiable claims: `agent_code`, `org_id`, `model_name`, `autonomy_level`, `created_at`, `expires_at`.
  * Verifiable offline by external gateways using the public key ID (`key_id`).
* **Machine Authentication Flow:**
  1. The agent client authenticates via `POST /api/runtime/auth` providing `agent_code` and plaintext machine secret (`ag_agent_...`).
  2. The server verifies credentials against SHA-256 hashes in `agent_credentials`.
  3. The server validates passport signature and expiration.
  4. Upon success, issues a short-lived **Machine JWT** (1-hour expiration) and initializes an active session in `agent_runtime_sessions`.

### The 5-Role Enterprise RBAC Model

Human users belong to one of five established organizational IAM roles:

| Role | Classification | Permissions & Responsibilities |
| :--- | :--- | :--- |
| **`ADMIN`** | Organization Administrator | Full control within tenant: manages users, invites, policies, agent provisioning, API keys, and tenant settings. |
| **`MANAGER`** | Operational Supervisor | Approves or rejects `REVIEW` requests in the approval queue; monitors agent activities, budgets, and operational performance. |
| **`SECURITY_OFFICER`** | Security Administrator | Configures guardrails, manages circuit breakers, defines security policies, conducts simulations, and oversees incident response. |
| **`AUDITOR`** | Compliance & Audit | Read-only inspection authority: views immutable audit logs, decision histories, provenance graphs, and compliance reports. Cannot modify configuration. |
| **`AGENT`** | AI Machine Identity | Runtime execution identity. **Blocked from accessing the human web dashboard.** Authenticates strictly via machine credentials or Machine JWTs. |

### Platform Administration vs. Tenant Scoping

AGENTGUARD maintains a strict distinction between organization-scoped roles and platform-level operations:

* **Platform Super Admin (`SUPER_ADMIN`):**
  * A dedicated platform-level role used for global infrastructure management.
  * Accesses cross-organization license provisioning, global health checks, platform telemetry, and tenant onboarding (`/api/platform/*`).
  * Has cross-tenant visibility only when explicitly requested; cannot silently bypass tenant audit logging.
* **Organization Roles:**
  * All organizational roles (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`) are strictly scoped to their assigned `org_id`.
  * Attempting to access agents, decisions, policies, or users belonging to another tenant yields an immediate `403 Forbidden (Cross-organization access is strictly prohibited)`.

### Tenant Isolation Guarantees

Tenant boundaries are enforced at the backend dependency level (`backend/core/deps.py:check_org_isolation`):

1. **Identity Binding:** The caller's `org_id` is derived authoritatively from the verified database user or agent record, never trusted from unverified request headers or client-supplied bodies.
2. **Database Query Scoping:** Every query targeting agents, policies, decisions, approvals, or telemetry applies an explicit `.filter(Model.org_id == current_user.org_id)` clause.
3. **Bring-Your-Own-Key (BYOK) Encryption:** Organizations can configure dedicated AWS KMS, GCP KMS, or HashiCorp Vault key ARNs for tenant-isolated encryption (`models.Organization.kms_key_arn`).

---

## Technology Stack

| Layer | Technology | Version | Purpose in AGENTGUARD |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | Next.js (App Router) | `14.2.15` | Enterprise operations console, server-rendered layouts, route guards |
| **Frontend UI & Styling** | React, Tailwind CSS | React `18.3.1`, Tailwind `3.4.14` | Component architecture, responsive dark-mode styling |
| **Icons & Visualization** | Lucide React, Recharts | Lucide `0.453.0`, Recharts `2.13.0` | Operational dashboards, real-time metrics, risk distribution charts |
| **Backend Framework** | FastAPI | `0.100.0+` | High-performance asynchronous REST API and WebSocket server |
| **Data Validation** | Pydantic v2 | `2.0.0+` | Strict schema validation, request/response models, field typing |
| **ORM & Database** | SQLAlchemy 2.0, PostgreSQL | SQLAlchemy `2.0.0+`, Postgres `15+` | Relational data persistence, schema models, transactions |
| **Database Driver** | psycopg2-binary | `2.9.0+` | PostgreSQL connection pool and adapter |
| **Authentication** | Supabase Auth, python-jose, passlib | python-jose `3.3.0+`, bcrypt `4.0.1` | JWT cryptographic verification, password hashing, API key hashes |
| **Real-Time WebSockets** | Starlette / WebSockets | `11.0+` | Live decision broadcasting, approval alerts, dashboard updates |
| **Task Queue & Broker** | Celery, Redis | Celery `5.3.0+`, Redis `4.5.0+` | Background scheduled reports, webhook deliveries, audit export |
| **Reporting Engine** | ReportLab, OpenPyXL | ReportLab `4.0.0+`, OpenPyXL `3.1.0+` | Enterprise PDF and Excel compliance report generation |
| **Python SDK** | Requests, Setuptools | Requests `2.28.0+` | Agent client, LangChain callbacks, CrewAI governance middleware |
| **TypeScript SDK** | TypeScript, Node.js | TypeScript `5.0.0+` | Node.js client, runtime authorization, tool proxy dispatch |
| **Testing** | Pytest, Pytest-Asyncio | Pytest `8.0+` | Unit tests, API integration tests, penetration and security suites |
| **Containers & Deploy** | Docker, Docker Compose | Compose `3.8` | Containerized development, API, Redis, Celery workers |

---

## Repository Structure

```text
AGENTGUARD/
├── .dockerignore                     # Docker build exclusions
├── .gitignore                        # Git version control exclusions
├── Dockerfile                        # Multi-stage production container build (FastAPI + ReportLab)
├── docker-compose.yml                # Multi-service composition (API, Redis, Celery Worker, Beat)
├── logo.png                          # Official AGENTGUARD logo asset
├── render.yaml                       # Cloud deployment blueprint for Render (Backend API)
├── vercel.json                       # Cloud deployment configuration for Vercel (Next.js Frontend)
├── README.md                         # Authoritative project README
│
├── backend/                          # FastAPI Backend Application Root
│   ├── config.py                     # Centralized settings (Pydantic / python-dotenv)
│   ├── database.py                   # SQLAlchemy engine, session factory, connection pooling
│   ├── models.py                     # Database models (User, Agent, Policy, Decision, etc.)
│   ├── schemas.py                    # Pydantic request, response, and evaluation schemas
│   ├── main.py                       # FastAPI application entrypoint, lifespan, and /ws endpoint
│   ├── celery_app.py                 # Celery application configuration & scheduled task beat
│   ├── ws_manager.py                 # WebSocket connection manager with ticket auth
│   ├── bootstrap.py                  # Database schema bootstrap & canonical SaaS plan seeding
│   ├── requirements.txt              # Production Python package manifest
│   ├── .env.example                  # Backend environment variable template
│   │
│   ├── core/                         # Core security & authentication dependencies
│   │   ├── deps.py                   # Auth dependencies, token verifiers, tenant checks
│   │   ├── permissions.py            # RBAC permission constants & role-permission matrix
│   │   ├── security.py               # Password hashing & JWT generation helpers
│   │   └── supabase_admin.py         # Supabase service role client wrapper
│   │
│   ├── engines/                      # Core Governance & Evaluation Engines
│   │   ├── predictive_action_control_engine.py # PACE sequence analyzer, reachability, intervention planner
│   │   ├── pace_evaluator.py         # PACE benchmark evaluation suite & Brier score metrics
│   │   ├── policy_engine.py          # Deterministic policy rules evaluation
│   │   ├── risk_engine.py            # Risk calculation & dynamic anomaly scoring
│   │   ├── circuit_breaker.py        # Automatic and manual agent circuit-breaker controls
│   │   ├── intent_engine.py          # Tool parameter validation & prompt injection detection
│   │   ├── pii_engine.py             # PII entity detection, masking, and redaction
│   │   ├── output_guardrails_engine.py # Toxicity and factual hallucination grounding guardrails
│   │   └── simulation_engine.py      # In-memory simulation runner for comparative evaluations
│   │
│   ├── routers/                      # Domain API Routers (Mounted under /api and /api/v1)
│   │   ├── runtime.py                # Machine auth, 12-stage authorize, execute, heartbeat, guardrails
│   │   ├── decisions.py              # Decision audit history, PACE pre-flight evaluate & execute
│   │   ├── simulation.py             # Simulation scenarios, runs, and persistent evaluation datasets
│   │   ├── approvals.py              # Human approval queue listing and resolution
│   │   ├── agents.py                 # Agent lifecycle management, passports, and credentials
│   │   ├── policies.py               # Deterministic policy creation, toggle, and rule management
│   │   ├── iam.py                    # User directory, roles, permissions, API key generation
│   │   ├── auth.py                   # Login, register, OTP verification, WebSocket tickets
│   │   ├── audit.py                  # Immutable audit trail queries and SIEM streaming export
│   │   ├── reports.py                # PDF and Excel compliance report generation
│   │   └── platform.py               # Global Super Admin platform management
│   │
│   ├── services/                     # Business Logic & Infrastructure Services
│   │   ├── runtime_authorization_service.py # 12-stage pre-flight execution pipeline
│   │   ├── tool_proxy_service.py     # SSRF-protected Forward Tool Proxy execution
│   │   ├── passport_service.py       # Ed25519 passport issuance and cryptographic verification
│   │   ├── machine_auth_service.py   # Machine credential validation and Machine JWT issuance
│   │   └── sandbox_service.py        # Isolated external sandbox execution manager
│   │
│   ├── tasks/                        # Celery background asynchronous task definitions
│   ├── storage/                      # Local file storage for generated compliance reports
│   ├── scripts/                      # Database migration and demo organization seeding scripts
│   └── tests/                        # Automated test suites (Pytest)
│
├── frontend/                         # Next.js 14 Frontend Application
│   ├── package.json                  # Frontend dependencies and build scripts
│   ├── tsconfig.json                 # TypeScript compiler configuration
│   ├── tailwind.config.js            # Tailwind CSS design system tokens
│   ├── .env.example                  # Frontend public environment template
│   ├── public/                       # Static brand assets (logo.png)
│   └── src/
│       ├── app/                      # Next.js App Router routes (59 verified pages)
│       │   ├── (app)/                # Authenticated enterprise console pages
│       │   ├── (auth)/               # Login, register, OTP, forgot-password routes
│       │   ├── platform/             # Super Admin global platform management views
│       │   └── layout.tsx            # Root HTML layout and providers
│       ├── components/               # Reusable React UI components and layouts
│       ├── lib/                      # API client, Supabase browser client, utilities
│       └── middleware.ts             # Route authentication guard & session check
│
├── sdks/                             # Official Client Libraries
│   ├── python/                       # Official Python SDK (`agentguard`)
│   │   ├── pyproject.toml            # Python packaging manifest
│   │   └── agentguard/
│   │       ├── client.py             # Synchronous AgentGuardClient
│   │       ├── langchain_handler.py  # LangChain callback handler
│   │       └── crewai_middleware.py  # CrewAI action interception middleware
│   └── typescript/                   # Official TypeScript / Node.js SDK (`@agentguard/sdk`)
│       ├── package.json              # NPM package manifest
│       ├── tsconfig.json             # TypeScript build configuration
│       └── src/
│           ├── client.ts             # Typed AgentGuardClient
│           ├── errors.ts             # Typed governance and circuit breaker errors
│           └── index.ts              # Package exports
│
├── LICENSE                           # Official Apache License 2.0
├── SECURITY.md                       # Security policy & vulnerability disclosure guide
├── CONTRIBUTING.md                   # Contributor guide, code standards & testing workflow
├── CHANGELOG.md                      # Release notes & version changelog
│
├── docs/                             # Authoritative Documentation, Guides & Runbooks
│   ├── README.md                     # Master documentation index
│   ├── architecture/                 # System flow & architectural specifications
│   ├── guides/                       # Local setup, configuration, API, SDK & testing guides
│   ├── runbooks/                     # Production deployment & development runbooks
│   ├── security/                     # Enterprise IAM & permission matrix specifications
│   ├── evaluation/                   # PACE benchmark & dataset evaluation guides
│   ├── specifications/               # Functional requirements, UI page directory & design system
│   └── reports/                      # Production readiness, security & UAT audit reports
│
├── cleanup_reports/                  # Historical database & repository cleanup audit logs
└── test_fixtures_uat/                # Test fixtures for dataset validation and penetration testing
```

---

## Prerequisites

Before setting up AGENTGUARD, ensure the following tools are installed on your host system:

* **Python:** Version `3.10.x` or `3.11.x` (verified with Python 3.10 on Windows x64).
* **Node.js:** Version `18.x` or `20.x LTS` (includes `npm`).
* **Git:** Version `2.30+`.
* **Database:**
  * **Development / Testing:** SQLite is supported out of the box (`sqlite:///./agentguard.db`).
  * **Production:** PostgreSQL `15+` (hosted via Supabase or AWS RDS).
* **Redis (Optional for Local, Required for Production):** Redis `7+`. When Redis is not configured, Celery tasks execute in synchronous eager mode, and rate limiting falls back to local in-memory storage.
* **Docker & Docker Compose (Optional):** Required if running via containerized deployment.

---

## Installation & Local Development

### 1. Clone Repository

```powershell
git clone https://github.com/bhataakib02/agentguard.git
cd agentguard
```

### 2. Backend Setup (PowerShell / Windows)

```powershell
# 1. Enter backend directory
cd backend

# 2. Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install backend dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure local environment variables
Copy-Item .env.example .env

# Edit backend/.env to set:
# ENVIRONMENT=development
# SECRET_KEY=agentguard-dev-stable-signing-key-2026-secure
# DATABASE_URL=sqlite:///./agentguard_dev.db

# 5. Initialize database tables and canonical SaaS plans
python bootstrap.py

# 6. (Optional) Seed demo organizations (ACME FinTech, CyberShield, etc.)
$env:ALLOW_DEMO_SEED = "true"
python scripts/seed_demo_orgs.py

# 7. Start FastAPI development server with hot-reload
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

* **Backend API Base:** `http://127.0.0.1:8000/api`
* **Interactive Swagger UI:** `http://127.0.0.1:8000/docs`
* **Interactive ReDoc:** `http://127.0.0.1:8000/redoc`
* **WebSocket Endpoint:** `ws://127.0.0.1:8000/ws`

### 3. Frontend Setup

In a new terminal window:

```powershell
# 1. Enter frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Configure local environment variables
Copy-Item .env.example .env.local

# Ensure frontend/.env.local points to local backend:
# NEXT_PUBLIC_API_URL=http://localhost:8000/api
# NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
# NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key

# 4. Start Next.js development server
npm run dev
```

* **Frontend Application:** `http://localhost:3000`

### 4. Bash / Linux / macOS Alternative

```bash
# Backend Setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bootstrap.py
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend Setup (in separate terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Configuration & Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Required? | Default / Example | Purpose |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | **Yes** | `development` | Environment tier (`development`, `test`, `production`). In production, strict secret checks and PostgreSQL are enforced. |
| `SECRET_KEY` | **Yes** | `<32+ Character Secret Key>` | HMAC-SHA256 signing secret for internal JWT tokens and tickets. |
| `DATABASE_URL` | **Yes** | `sqlite:///./agentguard_dev.db` (Dev) / `postgresql://...` (Prod) | Database connection URI. SQLite permitted only in development/test. |
| `AUTO_BOOTSTRAP_DB` | No | `True` (Dev) / `False` (Prod) | Provisions tables on startup if true. In production, run migrations explicitly. |
| `API_V1_STR` | No | `/api` | Primary API route prefix. |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated list of trusted client origins. |
| `SUPABASE_URL` | No | `https://your-project.supabase.co` | Supabase endpoint for JWT verification and external auth. |
| `SUPABASE_PUBLISHABLE_KEY` | No | `<supabase_publishable_key>` | Client-safe Supabase API key for token validation queries. |
| `SUPABASE_JWT_SECRET` | No | `<supabase_jwt_secret>` | Supabase JWT signing secret for fast local signature verification. |
| `SUPABASE_SERVICE_ROLE_KEY`| No | `<supabase_service_role_key>` | Server-side Supabase admin key for automated user provisioning. |
| `REDIS_URL` | Optional | `redis://localhost:6379/0` | Redis connection URL for Celery broker, caching, and rate limiting. |
| `CELERY_TASK_ALWAYS_EAGER` | No | `True` (when Redis absent) | Runs Celery tasks synchronously in the web process when true. |
| `OBJECT_STORAGE_PROVIDER` | No | `LOCAL` | Storage backend for compliance reports (`LOCAL` or `S3`). |
| `AGENTGUARD_ALLOW_LOCAL_TOOLS`| No | `false` | When true, permits the tool proxy to call `localhost` for local integration testing. |
| `SANDBOX_PROVIDER` | No | `NOT_CONFIGURED` | External isolated code execution provider (`NOT_CONFIGURED`, `REMOTE_WORKER`, `GVISOR`). |

> [!CAUTION]
> Never commit `.env` or `.env.local` files to version control. Production deployments must inject secrets via encrypted cloud secret managers (e.g., Render Environment Variables, AWS Secrets Manager, Vault).

### Frontend Configuration (`frontend/.env.local`)

| Variable | Required? | Default / Example | Purpose |
| :--- | :---: | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | **Yes** | `http://localhost:8000/api` | Base URL of the AGENTGUARD backend API. |
| `NEXT_PUBLIC_SUPABASE_URL` | **Yes** | `https://your-project.supabase.co` | Supabase project URL for browser-side authentication. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | **Yes** | `<supabase_publishable_key>` | Supabase anonymous public key for browser client. |

---

## API Reference & Core Workflows

### API Endpoints Overview

The backend mounts all domain routers under both `/api` and `/api/v1`. Interactive documentation is available locally at `/docs` (Swagger UI) and `/redoc` (ReDoc).

| Domain | Key Route | Method | Required Auth / Role | Description |
| :--- | :--- | :---: | :--- | :--- |
| **System Health** | `/health/live` | `GET` | Public | Liveness probe verifying process responsiveness. |
| **System Health** | `/health/ready` | `GET` | Public | Readiness probe verifying database connectivity. |
| **Machine Auth** | `/api/runtime/auth` | `POST` | Agent Credentials | Authenticates agent; issues 1-hour Machine JWT. |
| **Runtime Control** | `/api/runtime/authorize` | `POST` | Machine JWT or Human | 12-stage pre-flight authorization gate. |
| **Tool Execution** | `/api/runtime/execute` | `POST` | Machine JWT or Human | Executes tool via Forward Tool Proxy with gate token. |
| **Combined Gateway**| `/api/runtime/invoke` | `POST` | Machine JWT or Human | Authorizes and immediately executes if `ALLOW`. |
| **PACE Evaluation** | `/api/decisions/control/evaluate` | `POST` | Machine JWT or Human | Bounded PACE pre-flight evaluation and risk estimation. |
| **PACE Execution** | `/api/decisions/control/execute` | `POST` | Machine JWT or Human | Strict PACE execution boundary enforcement. |
| **PACE Benchmarks** | `/api/decisions/control/metrics` | `GET` | Human (`ADMIN`, `SEC_OFFICER`) | Benchmark precision, recall, FPR, F1, and Brier score. |
| **Human Approvals**| `/api/approvals` | `GET` | Human (`MANAGER`, `ADMIN`) | Lists pending approval requests. |
| **Human Approvals**| `/api/approvals/{id}/act` | `POST` | `MANAGER`, `ADMIN`, `SUPER_ADMIN` | Approves or rejects a pending review request. |
| **Simulation Lab** | `/api/simulation/runs` | `POST` | `ADMIN`, `SECURITY_OFFICER`, `MANAGER` | Launches in-memory Baseline vs. PACE simulation. |
| **Eval Datasets** | `/api/simulation/eval-data` | `GET` | `ADMIN`, `SEC_OFFICER`, `MANAGER`, `AUDITOR` | Lists persisted evaluation datasets. |
| **Eval Datasets** | `/api/simulation/eval-data/import` | `POST` | `ADMIN`, `SECURITY_OFFICER`, `MANAGER` | Imports and validates action-sequence datasets. |
| **Guardrails** | `/api/runtime/scan-pii` | `POST` | Machine JWT or Human | Scans text/JSON and applies PII redaction/masking. |
| **Guardrails** | `/api/runtime/scan-output` | `POST` | Machine JWT or Human | Scans LLM output for toxicity and hallucination grounding. |

### Health & Readiness Probes

Verify that the backend process is running:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/live" -Method Get
```

```json
{
  "status": "ALIVE",
  "process": "RUNNING",
  "commit_sha": "1050217",
  "timestamp": "2026-10-16T16:45:00.000000+00:00"
}
```

Verify that the database connection is operational:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/ready" -Method Get
```

```json
{
  "status": "READY",
  "database": "CONNECTED",
  "commit_sha": "1050217",
  "timestamp": "2026-10-16T16:45:00.000000+00:00"
}
```

### Pre-Flight Action Evaluation Example

Submit a proposed agent action to the canonical PACE evaluator endpoint (`POST /api/decisions/control/evaluate`):

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer <YOUR_MACHINE_OR_USER_TOKEN>"
}

$body = @{
    agent_code = "AG-101"
    action = "QUERY"
    resource = "DB:CUSTOMER_RECORDS"
    parameters = @{
        query = "SELECT id, name, email FROM customers WHERE status = 'ACTIVE' LIMIT 50"
    }
    amount = 0.0
    context = "Customer support inquiry lookup"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/decisions/control/evaluate" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Expected Response (`ALLOW`):**

```json
{
  "decision": "ALLOW",
  "decision_id": "dec_8f7b2c9a1d",
  "risk_score": 15,
  "confidence": 0.95,
  "execution_gate_token": "gate_3a7b9c1d2e4f5a6b",
  "mandatory_policy_violated": false,
  "sequence_indicators": {
    "window_size": 10,
    "events_evaluated": 3,
    "patterns_detected": [],
    "sequence_risk_delta": 0,
    "explanation": "Normal operational pattern within expected frequency bounds."
  },
  "reachability": {
    "prohibited_state_reachable": false,
    "search_depth_limit": 4,
    "states_explored": 6,
    "chains": []
  },
  "intervention_plan": {
    "selected_intervention": "ALLOW_WITHOUT_INTERVENTION",
    "disruption_level": 0,
    "enforcement_status": "ENFORCED",
    "rationale": "Proposed action satisfies all deterministic policies and presents low sequence risk."
  }
}
```

### Tool Execution Gateway Example

Consume the execution gate token to dispatch the approved tool call through the Forward Tool Proxy (`POST /api/runtime/execute`):

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer <YOUR_MACHINE_OR_USER_TOKEN>"
}

$body = @{
    execution_gate_token = "gate_3a7b9c1d2e4f5a6b"
    tool_name = "customer_database_query"
    parameters = @{
        limit = 50
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/runtime/execute" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

---

## Software Development Kits (SDKs)

AGENTGUARD includes official, native client libraries located in the `sdks/` directory.

> [!NOTE]
> The SDKs are maintained within this repository for local integration and testing. They are not currently published to public package registries (PyPI / npm).

### Python SDK (`sdks/python`)

* **Package Directory:** `sdks/python`
* **Supported Python Versions:** Python `>= 3.9`
* **Installation (Editable Local Mode):**

```powershell
cd sdks/python
pip install -e .
```

* **Basic Usage Example:**

```python
from agentguard.client import AgentGuardClient

# Initialize client with machine credentials
client = AgentGuardClient(
    agent_code="AG-FIN-01",
    agent_key="ag_agent_your_plaintext_credential_here",
    base_url="http://localhost:8000"
)

# 1. Authenticate and acquire short-lived Machine JWT
token = client.authenticate()
print(f"Authenticated session: {token[:16]}...")

# 2. Pre-flight action authorization
decision = client.authorize(
    action_requested="TRANSFER_FUNDS",
    resource_target="PAYMENT_GATEWAY",
    amount=450.0,
    parameters={"recipient_account": "ACC-9921", "currency": "USD"}
)

print(f"Decision: {decision['decision']} | Risk: {decision['risk_score']}")

# 3. If ALLOW, execute tool through Forward Tool Proxy using gate token
if decision["decision"] == "ALLOW":
    result = client.execute(
        tool_name="stripe_payout",
        parameters={"recipient_account": "ACC-9921", "amount": 450.0},
        execution_gate_token=decision["execution_gate_token"]
    )
    print("Execution output:", result)
elif decision["decision"] == "REVIEW":
    print(f"Action held for human approval (Approval ID: {decision['approval_id']})")
```

* **LangChain Integration:** The Python SDK includes `agentguard.langchain_handler.AgentGuardCallbackHandler` to automatically intercept LangChain tool calls and enforce pre-flight decisions.
* **CrewAI Integration:** Includes `agentguard.crewai_middleware.AgentGuardCrewMiddleware` to govern multi-agent task delegations.

### TypeScript SDK (`sdks/typescript`)

* **Package Directory:** `sdks/typescript`
* **Build & Test:**

```powershell
cd sdks/typescript
npm install
npm run build
node tests/test_sdk.mjs
```

* **Basic Usage Example (ES Modules / TypeScript):**

```typescript
import { AgentGuardClient } from "@agentguard/sdk";

const client = new AgentGuardClient({
  agentCode: "AG-OPS-01",
  agentKey: "ag_agent_your_plaintext_credential_here",
  baseUrl: "http://localhost:8000",
  raiseOnRefusal: true
});

async function run() {
  // 1. Authenticate machine identity
  await client.authenticate();

  // 2. Pre-flight authorization
  const auth = await client.authorize({
    action: "READ",
    resource: "S3_BUCKET:REPORTS",
    parameters: { bucket: "finance-reports", key: "q3_audit.pdf" }
  });

  if (auth.decision === "ALLOW") {
    // 3. Execute via tool proxy
    const res = await client.execute({
      toolName: "s3_fetch",
      parameters: { key: "q3_audit.pdf" },
      executionGateToken: auth.executionGateToken!
    });
    console.log("Fetch result:", res);
  }
}

run().catch(console.error);
```

---

## Simulation, Benchmarks, and Datasets

### In-Memory Simulation Lab

The Simulation Lab (`backend/routers/simulation.py`, `backend/engines/simulation_engine.py`) allows security teams to test agent policies against safe and adversarial scenarios before deploying them to production.

* **In-Memory Isolation:** Simulations execute strictly within transient in-memory structures. They **never dispatch actions to external tools** and **never write synthetic events to production audit logs**.
* **Predefined Scenario Library:** Includes 10 built-in test suites covering prompt injection attempts, unauthorized privilege escalation, data exfiltration, rate bursts, and financial limit violations.
* **Comparative Evaluation:** Runs both a **Baseline Policy Engine** (static permission check) and the **PACE Engine** side-by-side, producing:
  * Comparative confusion matrices (True Positives, False Positives, True Negatives, False Negatives).
  * Lead-time intervention statistics (actions intercepted before reaching terminal prohibited states).
  * Relative false-positive and false-negative delta analysis.

### Persistent Evaluation Datasets

Organizations can import, persist, and manage custom evaluation datasets (`POST /api/simulation/eval-data/import`):

* **Tenant Isolation:** Datasets are strictly scoped to the importing tenant (`models.EvaluationDataset.org_id`).
* **Validation & Hygiene:** Payloads are validated against strict JSON schemas. Payloads containing malformed syntax, unsupported action labels, or unmasked credentials are automatically rejected.
* **Role Enforcement:** Importing requires `ADMIN`, `SECURITY_OFFICER`, or `MANAGER`. The `AUDITOR` role has read-only access. Machine identities (`AGENT`) are blocked from dataset management.

---

## Testing & Verification

The AGENTGUARD repository includes a comprehensive, multi-layer automated test suite.

### Verified Test Suites

All tests listed below have been directly executed and verified against the repository:

| Test Suite File | Domain | Verified Result | Command |
| :--- | :--- | :---: | :--- |
| `backend/tests/test_predictive_action_control_engine.py` | PACE Engine, sequence risk, reachability, minimal intervention | **20 Passed** | `python -m pytest backend/tests/test_predictive_action_control_engine.py -q` |
| `backend/tests/test_sdk_suite.py` | Python SDK, authentication, authorization, error handling | **19 Passed** | `python -m pytest backend/tests/test_sdk_suite.py -q` |
| `backend/tests/test_tenant_security_penetration.py` | Multi-tenant isolation, cross-tenant penetration, BYOK scoping | **11 Passed** | `python -m pytest backend/tests/test_tenant_security_penetration.py -q` |
| `backend/tests/test_dynamic_dataset_evaluation.py`<br>`backend/tests/test_evaluation_datasets_persistence.py` | Dataset persistence, validation rules, simulation metrics | **35 Passed** | `python -m pytest backend/tests/test_dynamic_dataset_evaluation.py backend/tests/test_evaluation_datasets_persistence.py -q` |
| `sdks/typescript/tests/test_sdk.mjs` | TypeScript SDK instantiation, error classes, output scanning | **5 Passed** | `node sdks/typescript/tests/test_sdk.mjs` |
| `frontend/package.json (lint)` | Next.js / ESLint static code quality & hook dependencies | **0 Errors** | `npm --prefix frontend run lint` |
| `frontend/package.json (build)` | Next.js production build & static page generation | **59 Routes OK** | `npm --prefix frontend run build` |

### Verification Checklist

When validating an installation or assessing security posture, confirm that:

- [x] **Unauthenticated requests are rejected:** Calling protected endpoints without a valid token returns `401 Unauthorized`.
- [x] **Cross-tenant access is blocked:** Attempting to query another organization's agents or decisions returns `403 Forbidden`.
- [x] **Mandatory policy prohibitions are non-overridable:** A prohibited action receives `REFUSE` regardless of low sequence risk.
- [x] **Gate tokens are single-use:** Re-using an execution gate token yields `400 Bad Request (GATE_TOKEN_REPLAYED)`.
- [x] **Gate tokens expire:** Tokens older than 300 seconds are rejected with `GATE_TOKEN_EXPIRED`.
- [x] **SSRF protection is active:** Tool proxy calls to loopback (`127.0.0.1`), private subnets, and cloud metadata (`169.254.169.254`) are blocked.
- [x] **Machine agents cannot access the UI:** User accounts with role `AGENT` are blocked from human management routes.
- [x] **Simulations are isolated:** Running simulations does not append synthetic records to production audit logs.

---

## Security Model & Responsible Disclosure

### Defense-in-Depth Architecture

1. **Least Privilege & Role Separation:** Five distinct organizational roles (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`) ensure strict operational separation. Approvals require supervisory authority (`MANAGER` or `ADMIN`); compliance auditing is read-only.
2. **Cryptographic Integrity:** Machine agent passports are signed with **Ed25519**. WebSockets require short-lived single-use tickets to prevent credential leakage in query parameters or access logs.
3. **SSRF Egress Defense:** The Forward Tool Proxy validates outbound URLs using `ipaddress` parsing, blocking loopback addresses, link-local addresses, private subnets, and cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
4. **Guardrail Defense:** Inbound payloads are scanned for PII (with regex and tokenized masking modes) and prompt injection markers. Outbound model responses are evaluated for toxicity thresholds and factual hallucination grounding against source contexts.
5. **No Ephemeral Secrets in Production:** When `ENVIRONMENT=production`, AGENTGUARD requires an explicit, high-entropy `SECRET_KEY` (minimum 32 characters) and a valid PostgreSQL connection string. Insecure default keys and SQLite fallbacks cause immediate startup termination.

### Security Maturity & Status

> [!NOTE]
> AGENTGUARD's security design reflects defense-in-depth principles and pre-flight interception invariants. However, the software has not undergone independent third-party SOC 2 or external penetration audit certification. Organizations evaluating the system should conduct internal threat modeling and security reviews prior to production deployment.

### Reporting Vulnerabilities

If you identify a security vulnerability or potential exposure in AGENTGUARD:

* Please open a private security advisory on the GitHub repository or contact the repository maintainers directly.
* Provide a complete description of the issue, affected components, reproduction steps, and potential impact.
* Allow reasonable time for remediation before public disclosure.

---

## Deployment Topologies

### Docker Compose Local Deployment

The repository includes a production-style multi-service composition (`docker-compose.yml`) defining:
* `agentguard-api`: FastAPI backend container running on port `8000`.
* `agentguard-redis`: Redis 7 alpine cache and Celery broker on port `6379`.
* `agentguard-worker`: Celery asynchronous worker process for report generation and background tasks.
* `agentguard-beat`: Celery Beat periodic scheduler.

```powershell
# Set required environment variables
$env:DATABASE_URL = "postgresql://user:password@host:5432/dbname"
$env:SECRET_KEY = "your-secure-production-random-32-byte-hex-key"

# Build and start services
docker-compose up --build -d
```

Verify service health:

```powershell
docker-compose ps
```

### Cloud Production Deployment (Render + Vercel)

The repository provides infrastructure configurations for cloud platforms:

1. **Backend Service (Render):**
   * Configured via `render.yaml`.
   * Type: Web Service (Python environment).
   * Build Command: `pip install -r requirements.txt` (executed in `rootDir: backend`).
   * Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT --ws-ping-interval 20 --ws-ping-timeout 20`.
   * Health Check: `/health/live`.

2. **Frontend Service (Vercel):**
   * Configured via `vercel.json`.
   * Framework: Next.js 14.
   * Build Command: `cd frontend && npm run build`.
   * Output Directory: `frontend/.next`.

---

## Known Limitations & Current Status

To ensure complete technical transparency, the following table lists current limitations and operational boundaries:

| Area | Current Status | Operational Limitation / Requirement |
| :--- | :--- | :--- |
| **External Sandboxes** | Implemented with Limitations | External sandbox code execution (`backend/services/sandbox_service.py`) defaults to `SANDBOX_PROVIDER=NOT_CONFIGURED`. Full gVisor or Firecracker isolation requires an external worker infrastructure deployment. |
| **Tool Execution** | Dual-Path Architecture | AGENTGUARD provides an SSRF-protected Forward Tool Proxy. However, if agents execute tools client-side, enforcement relies on the client SDK respecting the returned `ALLOW`/`REFUSE` decision and gate token. |
| **Background Queues** | Optional Local Fallback | Celery workers and Beat scheduler require a live Redis instance. If Redis is absent, Celery runs in synchronous eager mode (`CELERY_TASK_ALWAYS_EAGER=True`). |
| **Payment Gateways** | Schema Modeled Only | Multi-tenant SaaS billing plans and license limits are modeled in the database (`models.Plan`, `models.License`), but direct integrations with Stripe or Razorpay webhooks are not implemented. |
| **Evaluation Metrics** | Benchmark-Derived | PACE evaluation metrics (Precision, Recall, FPR, F1, Brier score) are calculated against deterministic benchmark suites and synthetic fixtures, not derived from live production customer telemetry. |
| **SDK Distribution** | Source Repository Only | Python and TypeScript SDKs reside in `sdks/` and can be built/installed locally, but are not currently published to PyPI or the global npm registry. |
| **Repository License** | Apache-2.0 | Full open-source [Apache License 2.0](LICENSE) is provided at the repository root and is consistent across repository SDKs and source code. |

---

## Project Roadmap

The following roadmap outlines the current status of features and planned extensions:

### Implemented Capabilities
- [x] 12-Stage pre-flight runtime authorization kernel.
- [x] PACE sequence-aware risk assessment and bounded reachability graph.
- [x] Cryptographic Ed25519 agent passport verification.
- [x] Single-use execution gate tokens with replay prevention and 300s TTL.
- [x] SSRF-protected Forward Tool Proxy.
- [x] Five-role enterprise RBAC (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`) and `SUPER_ADMIN`.
- [x] Multi-tenant data scoping and BYOK encryption configuration.
- [x] Real-time WebSocket decision broadcasting with ticket authentication.
- [x] In-memory Simulation Lab with 10 scenario suites.
- [x] Persistent evaluation dataset manager with validation hygiene.
- [x] Native Python and TypeScript SDKs with LangChain / CrewAI integration.
- [x] Next.js 14 App Router enterprise operational dashboard (59 routes).

### Proposed Future Work
- [ ] Direct publishing of official Python SDK to PyPI and TypeScript SDK to npm.
- [ ] Out-of-the-box Helm charts and Kubernetes manifests for enterprise cluster deployments.
- [ ] Production-ready gVisor and Firecracker sandbox execution daemon integrations.
- [ ] Native automated Stripe and Razorpay webhook billing integration.
- [ ] Automated CI/CD workflow definitions (GitHub Actions) for linting, type-checking, and test automation.

---

## Contributing

We welcome contributions to AGENTGUARD. Please adhere to the following workflow:

1. **Fork or Branch:** Create a feature branch from `main`:
   ```powershell
   git checkout -b feature/your-feature-name
   ```
2. **Follow Security Invariants:** Ensure that changes preserve the non-bypassability of the pre-flight kernel, multi-tenant isolation, and strict input validation.
3. **Verify Tests:** Execute relevant backend and SDK test suites before submitting changes:
   ```powershell
   python -m pytest backend/tests/ -q
   node sdks/typescript/tests/test_sdk.mjs
   npm --prefix frontend run lint
   ```
4. **Submit a Pull Request:** Open a pull request against `main` with a clear description of changes, rationale, and verification results.

---

## License & Acknowledgments

* **License:** AGENTGUARD is licensed under the [Apache License, Version 2.0](LICENSE). See [LICENSE](LICENSE) for the full license text.
* **Contributing & Security:** See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and [SECURITY.md](SECURITY.md) for vulnerability reporting.
* **Changelog:** See [CHANGELOG.md](CHANGELOG.md) for release history and unreleased baseline notes.
* **Acknowledgments:**
  * Built using [FastAPI](https://fastapi.tiangolo.com/), [Next.js](https://nextjs.org/), [SQLAlchemy](https://www.sqlalchemy.org/), [Tailwind CSS](https://tailwindcss.com/), and [Lucide Icons](https://lucide.dev/).
  * Inspired by zero-trust architecture principles and defense-in-depth security engineering for autonomous systems.

---

## Documentation Index

For in-depth architectural specifications, developer guides, operational runbooks, and audit reports, refer to the master index at [docs/README.md](docs/README.md):

* **Developer & Operator Guides:**
  * [Local Setup Guide](docs/guides/LOCAL_SETUP.md) — Workstation installation and verification
  * [Configuration Guide](docs/guides/CONFIGURATION.md) — Environment variables and security keys
  * [API Reference Guide](docs/guides/API_GUIDE.md) — REST and WebSocket endpoints
  * [SDK Integration Guide](docs/guides/SDK_GUIDE.md) — Python and TypeScript SDK usage
  * [Testing & Verification Guide](docs/guides/TESTING_GUIDE.md) — Regression suites and quality verification
* **Architecture & Security:**
  * [Master System Flow & Operational Specification](docs/architecture/AGENTGUARD_MASTER_SYSTEM_FLOW.md)
  * [Enterprise IAM & Permission Matrix](docs/security/IAM_ROLE_MATRIX.md)
* **Specifications & Design System:**
  * [UI Design System Specification](docs/specifications/UI_DESIGN_SYSTEM.md)
  * [Complete UI Page Directory (59 Routes)](docs/specifications/UI_PAGE_DIRECTORY.md)
  * [Functional Requirements Specification](docs/specifications/FUNCTIONAL_REQUIREMENTS.md)
  * [Master Feature Matrix](docs/specifications/MASTER_FEATURE_MATRIX.md)
* **Operational Runbooks:**
  * [Production Deployment Runbook](docs/runbooks/DEPLOYMENT_RUNBOOK.md)
  * [Local Development Workflow Guide](docs/runbooks/DEVELOPMENT_WORKFLOW.md)
* **Evaluation & Reports:**
  * [Dynamic Dataset & Benchmark Evaluation](docs/evaluation/DATASET_EVALUATION.md)
  * [Cleanup and Production Consistency Report](docs/reports/CLEANUP_AND_PRODUCTION_CONSISTENCY_REPORT.md)
  * [Secret Remediation Report](docs/reports/PHASE_SECRET_REMEDIATION_REPORT.md)
  * [Deployment Configuration Fix Report](docs/reports/PHASE_DEPLOYMENT_FIX_REPORT.md)

---

<p align="center">
  <strong>AGENTGUARD — Governing Autonomous AI Actions Through Deterministic Policy, Sequence-Aware Risk, and Provable Pre-Flight Authorization.</strong>
</p>
