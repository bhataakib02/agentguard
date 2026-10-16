# Enterprise IAM Architecture & Permission Matrix

This document defines the authoritative identity and access management (IAM) model for **AGENTGUARD**, detailing role hierarchies, granular permission matrices, and platform operator isolation.

---

## 1. Canonical 5-Role Organizational Model

Every human user and autonomous entity inside a tenant organization is assigned one of the five canonical roles:

| Role | Hierarchy Level | Target Persona | Core Governance Scope |
| :--- | :---: | :--- | :--- |
| **`ADMIN`** | **Level 8** | Tenant Organization Administrator | Full tenant governance: user management, team billing, API key provisioning, system integrations, and global tenant settings. |
| **`MANAGER`** | **Level 6** | Team Lead / Operational Manager | Operational oversight: agent configuration, team delegation, PACE human-in-the-loop approval decisions, and performance review. |
| **`SECURITY_OFFICER`** | **Level 5** | Security Analyst / SecOps Engineer | Security posture enforcement: policy authoring, threat incident triage, emergency agent quarantine, and prompt injection rule updates. |
| **`AUDITOR`** | **Level 2** | Compliance Reviewer / External Auditor | Read-only compliance: cryptographic audit log inspection, evidence exports, compliance report verification, and read-only policy review. |
| **`AGENT`** | **Level 1** | Autonomous Machine Identity | Machine entity: action evaluation requests, tool invocation via capability tokens, and telemetry emission. Cannot log in to web UI. |

*(Optional fine-grained operational sub-roles `DEVELOPER` (Level 7), `OPERATOR` (Level 4), `ANALYST` (Level 3), and `USER` (Level 1) provide specialized operational tiers within organization boundaries).*

---

## 2. Granular Role × Permission Matrix

The following matrix reflects the exact permissions enforced by `backend/core/permissions.py` and `frontend/src/lib/permissions.ts`:

| Functional Capability | `ADMIN` | `MANAGER` | `SECURITY_OFFICER` | `AUDITOR` | `AGENT` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Manage Tenant Users & Invitations** | ✅ Full | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |
| **Manage Subscription & Billing** | ✅ Full | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |
| **Create & Revoke API Keys** | ✅ Full | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |
| **Create & Configure Agents** | ✅ Full | ✅ Full | ❌ Read Only | ❌ Read Only | ❌ Denied |
| **Approve Escalated PACE Actions (HITL)** | ✅ Full | ✅ Full | ✅ Full | ❌ Denied | ❌ Denied |
| **Author & Modify Governance Policies** | ✅ Full | ❌ Read Only | ✅ Full | ❌ Read Only | ❌ Denied |
| **Trigger Emergency Agent Quarantine** | ✅ Full | ❌ Denied | ✅ Full | ❌ Denied | ❌ Denied |
| **Resolve Security Incidents** | ✅ Full | ❌ Read Only | ✅ Full | ❌ Read Only | ❌ Denied |
| **View Cryptographic Audit Logs** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ❌ Denied |
| **Generate & Export Compliance Reports** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ❌ Denied |
| **Request PACE Action Evaluation** | ❌ N/A | ❌ N/A | ❌ N/A | ❌ N/A | ✅ Full |

---

## 3. Platform Operator Scope (`SUPER_ADMIN`)

AGENTGUARD strictly separates tenant-level administration from platform-wide operations:

1. **Global Platform Actor:** `SUPER_ADMIN` (Hierarchy Level 9) is reserved exclusively for the host infrastructure operator. This role is responsible for cross-tenant system health, license extension, and platform security aggregation.
2. **Strict Tenant Exclusion:** A `SUPER_ADMIN` does not belong to any customer tenant organization and never appears in tenant user rosters, quota counts, or team directories.
3. **Immutability of Role Assignment:** In `backend/core/permissions.py`, `can_manage_role()` explicitly blocks tenant administrators from assigning, inviting, or escalating users to `SUPER_ADMIN`.
4. **Endpoint Protection on `/api/platform/security`:** Protected by FastAPI dependency `Depends(require_super_admin)`. The backend verifies the session token against database records and rejects all tenant roles (`ADMIN`, `SECURITY_OFFICER`, etc.) with `403 Forbidden`. Caller-forged headers (`X-Role: SUPER_ADMIN`) are strictly ignored.
