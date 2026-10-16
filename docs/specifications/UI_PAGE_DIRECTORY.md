# Complete UI Page Directory & Navigation Map

**Classification:** Comprehensive Frontend Route Directory  
**Total Routes:** 59 Next.js App Router Pages  
**Target:** AGENTGUARD Enterprise Dashboard (`frontend/src/app`)  

---

## 1. Public & Authentication Pages

1. **`/(auth)/login`:** Enterprise user login with email/password and Supabase authentication.
2. **`/(auth)/register`:** New tenant organization registration and initial administrator provisioning.
3. **`/(auth)/forgot-password`:** Self-service password reset request workflow.
4. **`/(auth)/reset-password`:** Password reset completion interface via cryptographic token.
5. **`/(auth)/accept-invite`:** User onboarding and invitation acceptance flow.
6. **`/` (Root):** Enterprise landing page with architectural overview and documentation links.

---

## 2. Organization Dashboard & Operational Views (`/(app)`)

1. **`/(app)/dashboard`:** Main organization command center with real-time risk gauges, agent counts, and decision feeds.
2. **`/(app)/agents`:** Agent registry directory displaying status, framework, risk scores, and passport details.
3. **`/(app)/agents/create`:** Wizard for provisioning new autonomous agents and issuing capability credentials.
4. **`/(app)/agents/[id]`:** Detailed agent passport profile, telemetry graphs, and tool invocation history.
5. **`/(app)/agents/[id]/edit`:** Agent configuration, metadata update, and policy attachment interface.
6. **`/(app)/policies`:** Governance policy catalog displaying active rules, regex patterns, and enforcement modes.
7. **`/(app)/policies/create`:** Policy creation builder for authoring deterministic and heuristic guardrails.
8. **`/(app)/policies/[id]`:** Granular policy inspection, revision history, and conflict precedence review.
9. **`/(app)/approvals`:** Human-in-the-Loop (HITL) approval queue for escalated actions (`REVIEW` outcome).
10. **`/(app)/approvals/[id]`:** Deep-dive approval modal displaying action parameters, context, and override controls.
11. **`/(app)/audit`:** Immutable cryptographic audit log explorer with SHA-256 hash-chain verification.
12. **`/(app)/incidents`:** Security Incident & SOC triage dashboard for anomalous agent behaviors.
13. **`/(app)/incidents/[id]`:** Incident remediation console with quarantine controls and timeline reconstruction.
14. **`/(app)/analytics`:** FinOps and telemetry metrics displaying token spend, latency, and cost accounting.
15. **`/(app)/compliance`:** Compliance assessment center (SOC 2, ISO 42001, NIST AI RMF, EU AI Act).
16. **`/(app)/reports`:** Automated compliance report generator and export history (PDF, CSV, XLSX).
17. **`/(app)/simulation`:** Digital Twin simulation and adversarial red-team stress testing workbench.
18. **`/(app)/datasets`:** Evaluation dataset manager for persistent benchmark scenario versioning.
19. **`/(app)/datasets/[id]`:** Record-level dataset viewer displaying expected outcomes and attack payloads.

---

## 3. Organization Administration (`/(app)/admin`)

1. **`/(app)/admin/users`:** Organization user roster with role assignment (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`).
2. **`/(app)/admin/users/invite`:** Team invitation workflow with role pre-selection.
3. **`/(app)/admin/api-keys`:** API key provisioning and revocation center (`ag_live_pk_*`).
4. **`/(app)/admin/billing`:** Subscription plan management, quota utilization, and license status.
5. **`/(app)/admin/settings`:** Organization profile, branding customization, and security parameters.
6. **`/(app)/admin/webhooks`:** Webhook dispatch endpoint configuration with SSRF protection.
7. **`/(app)/admin/integrations`:** SIEM, Slack, PagerDuty, and third-party connector configuration.

---

## 4. Platform Administration (`/platform` — `SUPER_ADMIN` Only)

1. **`/platform`:** Platform command center displaying aggregate health, tenant counts, and global telemetry.
2. **`/platform/security`:** Authoritative global security posture displaying cross-tenant incidents, blocked executions, and quarantined identities.
3. **`/platform/organizations`:** Global tenant directory with provisioning and lifecycle controls.
4. **`/platform/organizations/[id]`:** Specific tenant detail inspection, user quotas, and license assignment.
5. **`/platform/licenses`:** Global license management, renewal, and extension console.
6. **`/platform/audit`:** Platform-level audit trail recording cross-tenant administrative interventions.
