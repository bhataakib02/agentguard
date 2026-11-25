# AGENTGUARD Comprehensive Database Tenant Isolation Matrix

This document provides a line-by-line inventory of all 50 application tables in the `public` database schema, detailing their tenant ownership model, data sensitivity, Row Level Security (RLS) policy design, and verified migration risks.

---

## Complete Table-by-Table Inventory

| # | Table Name | PK | org_id Present | org_id Nullable | Ownership Model | Authoritative Join Path | Sensitivity | Proposed RLS Policy Archetype | Migration Risk & Required Safeguards |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `organizations` | `id` | Root | N/A | Direct Tenant Root | `id = current_org_id()` | Critical | Direct Root Isolation | Low. Root tenant boundary. |
| 2 | `users` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Critical | Direct Tenant Isolation | Low. Self profile access allowed via `auth_user_id = auth.uid()`. |
| 3 | `agents` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. All child entities cascade from this table. |
| 4 | `api_keys` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Critical | Direct Tenant Isolation | Low. Key hashes must remain protected. |
| 5 | `audit_logs` | `id` | ✅ | ⚠️ **YES** | Direct Tenant / System | `org_id = current_org_id()` | High | **Immutable Tenant Read-Only** | **HIGH**. MUST be `FOR SELECT` only. Never grant UPDATE/DELETE to authenticated. |
| 6 | `policies` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. Policy engine rules. |
| 7 | `tools` | `id` | ✅ | ⚠️ **YES** | Hybrid (Global / Tenant) | `org_id = current_org_id() OR org_id IS NULL` | High | **Global + Tenant Hybrid** | **HIGH**. Global tools (`org_id IS NULL`) become invisible if policy lacks `OR org_id IS NULL`. |
| 8 | `webhook_endpoints`| `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. Endpoint delivery targets. |
| 9 | `scheduled_reports`| `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Tenant report configurations. |
| 10 | `report_histories` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Historical report records. |
| 11 | `security_incidents`| `id`| ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Critical | Direct Tenant Isolation | Low. Incident tracking data. |
| 12 | `runtime_risk_signals`|`id`| ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. Runtime telemetry signals. |
| 13 | `sandbox_execution_jobs`|`id`|✅| **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. External sandbox execution states. |
| 14 | `agent_budget_configs`|`id`|✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Organization spend caps. |
| 15 | `agent_executions` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. High-volume execution records. |
| 16 | `evaluation_datasets`| `id`| ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Benchmark test collections. |
| 17 | `evaluation_dataset_records`|`id`|✅|**NO**| Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Dataset item records. |
| 18 | `evaluation_scenarios`|`id`|✅| **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Scenario definitions. |
| 19 | `evaluation_scenario_records`|`id`|✅|**NO**| Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Scenario execution runs. |
| 20 | `siem_configs` | `id` | ✅ | ⚠️ **YES** | Hybrid (Global / Tenant) | `org_id = current_org_id() OR (org_id IS NULL AND is_super_admin())` | Critical | Direct Tenant + Admin Global | Medium. Nullable for global forwarders. |
| 21 | `siem_deliveries` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. SIEM export logs. |
| 22 | `user_invitations` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. Pending user invitations. |
| 23 | `licenses` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. Subscription licenses. |
| 24 | `license_usages` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Quota and usage counters. |
| 25 | `guardrail_rules` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. AI guardrails rules. |
| 26 | `integration_configs`|`id`| ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Critical | Direct Tenant Isolation | Low. OAuth and 3rd party secrets. |
| 27 | `network_policies` | `id` | ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | High | Direct Tenant Isolation | Low. Egress rules and allowlists. |
| 28 | `optimization_rules`|`id`| ✅ | **NO** | Direct Tenant | `org_id = current_org_id()` | Medium | Direct Tenant Isolation | Low. Performance rules. |
| 29 | `decisions` | `id` | ❌ | N/A | Child via Agent / User | `agent_id->agents.org_id` / `user_id->users.org_id` | Critical | Polymorphic Subquery Join | **HIGH**. Must enforce symmetric `WITH CHECK` on both `agent_id` and `user_id`. |
| 30 | `approval_requests` | `id` | ❌ | N/A | Child via Agent & Decision | `agent_id->agents.org_id` | Critical | Parent Subquery Join | Medium. Linked to `decisions.id` and `agents.id`. |
| 31 | `agent_credentials` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | Critical | Parent Subquery Join | Medium. High security credential secrets. |
| 32 | `agent_passports` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Cryptographic agent identities. |
| 33 | `agent_relationships`|`id`| ❌ | N/A | Dual Agent Child | `parent_agent_id` AND `child_agent_id` | High | **Dual Parent Subquery Join** | **HIGH**. MUST validate BOTH parent and child agents belong to `current_org_id()`. |
| 34 | `agent_runtime_sessions`|`id`|❌| N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Active agent execution states. |
| 35 | `anomaly_events` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Runtime anomaly alerts. |
| 36 | `behavior_profiles` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | Medium | Parent Subquery Join | Medium. Behavioral baselines. |
| 37 | `budgets` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | Medium | Parent Subquery Join | Medium. Granular agent budget limits. |
| 38 | `capability_tokens` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | Critical | Parent Subquery Join | Medium. Cryptographic delegation tokens. |
| 39 | `circuit_breakers` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Emergency trip states. |
| 40 | `permissions` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Action authorizations. |
| 41 | `provenance_events` | `id` | ❌ | N/A | Child via Agent & Decision | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Chain-of-custody telemetry. |
| 42 | `reputation_scores` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | Medium | Parent Subquery Join | Medium. Historical trust metrics. |
| 43 | `resource_usages` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | Low | Parent Subquery Join | Low. Token/compute consumption. |
| 44 | `risk_scores` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Risk evaluation metrics. |
| 45 | `security_tests` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. Automated penetration checks. |
| 46 | `simulations` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | High | Parent Subquery Join | Medium. PACE sandbox runs. |
| 47 | `transactions` | `id` | ❌ | N/A | Child via Agent | `agent_id->agents.org_id` | Critical | Parent Subquery Join | Medium. Financial/API transactions. |
| 48 | `sessions` | `id` | ❌ | N/A | Child via User | `user_id->users.org_id` | Critical | **Service Role Exclusive** | **HIGH**. MUST NOT be accessible to authenticated peers in same org. Revoke from PostgREST. |
| 49 | `notifications` | `id` | ❌ | N/A | Child via User | `user_id->users.org_id` | Medium | **User-Scoped Isolation** | Medium. Must isolate per `user_id` to prevent cross-user snooping within tenant. |
| 50 | `webhook_deliveries`| `id`| ❌ | N/A | Child via Webhook | `webhook_id->webhook_endpoints.org_id` | Medium | Parent Subquery Join | Medium. Webhook dispatch logs. |

---

## Global System Catalogs & Pre-Auth Tables

| Table Name | Primary Key | Application Purpose | RLS Policy Archetype | PostgREST Client Permissions |
|---|---|---|---|---|
| `plans` | `id` | Subscription tiers & feature flags | Read-Only to Authenticated | `SELECT` allowed; Writes denied. |
| `ai_models` | `id` | Catalog of approved LLM providers | Read-Only to Authenticated | `SELECT` allowed; Writes denied. |
| `capabilities` | `id` | Capability action types & boundaries | Read-Only to Authenticated | `SELECT` allowed; Writes denied. |
| `model_pricing` | `id` | Token input/output cost schedules | Read-Only to Authenticated | `SELECT` allowed; Writes denied. |
| `policy_rules` | `id` | AST condition rules for policies | Parent Join via `policies.org_id` | Governed by parent policy ownership. |
| `otp_challenges` | `id` | Pre-authentication HMAC challenge codes | **Service Role Exclusive** | **REVOKE ALL FROM anon, authenticated**. Zero PostgREST exposure. |
