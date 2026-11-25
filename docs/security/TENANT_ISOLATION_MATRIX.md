# AGENTGUARD Comprehensive Database Tenant Isolation Matrix

This document provides a line-by-line inventory of all 50 application tables in the `public` database schema, detailing their tenant ownership model, data sensitivity, Row Level Security (RLS) policy design, and migration risk.

---

## Complete Table-by-Table Inventory

| # | Table Name | PK | org_id | user_id | Ownership Model | FK Join Path to Tenant Org | Sensitivity | RLS Applicable | Safe to Enforce | Proposed Policy Design | Migration Risk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `organizations` | `id` | Root | ❌ | Direct Tenant Root | `id = org_id` | Critical | Required | Yes | `id = current_org_id() OR is_super_admin()` | Low |
| 2 | `users` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Critical | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 3 | `agents` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 4 | `api_keys` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Critical | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 5 | `audit_logs` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 6 | `policies` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 7 | `tools` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 8 | `webhook_endpoints` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 9 | `scheduled_reports` | `id` | ✅ | ✅ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 10 | `report_histories` | `id` | ✅ | ✅ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 11 | `security_incidents` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Critical | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 12 | `runtime_risk_signals` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 13 | `sandbox_execution_jobs` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 14 | `agent_budget_configs` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 15 | `agent_executions` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 16 | `evaluation_datasets` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 17 | `evaluation_dataset_records` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 18 | `evaluation_scenarios` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 19 | `evaluation_scenario_records` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 20 | `siem_configs` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Critical | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 21 | `siem_deliveries` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 22 | `user_invitations` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 23 | `licenses` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 24 | `license_usages` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 25 | `guardrail_rules` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 26 | `integration_configs` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Critical | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 27 | `network_policies` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | High | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 28 | `optimization_rules` | `id` | ✅ | ❌ | Direct Tenant | `org_id` | Medium | Required | Yes | `org_id = current_org_id() OR is_super_admin()` | Low |
| 29 | `decisions` | `id` | ❌ | ✅ | Child via Agent/User | `agent_id->agents.org_id` OR `user_id->users.org_id` | Critical | Required | Yes | Subquery join via `agents` or `users` | Medium |
| 30 | `approval_requests` | `id` | ❌ | ❌ | Child via Agent/Decision | `agent_id->agents.org_id` | Critical | Required | Yes | Subquery join via `agents` | Medium |
| 31 | `agent_credentials` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | Critical | Required | Yes | Subquery join via `agents` | Medium |
| 32 | `agent_passports` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 33 | `agent_relationships` | `id` | ❌ | ❌ | Child via Agent | `parent_agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 34 | `agent_runtime_sessions` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 35 | `anomaly_events` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 36 | `behavior_profiles` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | Medium | Required | Yes | Subquery join via `agents` | Medium |
| 37 | `budgets` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | Medium | Required | Yes | Subquery join via `agents` | Medium |
| 38 | `capability_tokens` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | Critical | Required | Yes | Subquery join via `agents` | Medium |
| 39 | `circuit_breakers` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 40 | `permissions` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 41 | `provenance_events` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 42 | `reputation_scores` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | Medium | Required | Yes | Subquery join via `agents` | Medium |
| 43 | `resource_usages` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | Low | Required | Yes | Subquery join via `agents` | Medium |
| 44 | `risk_scores` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 45 | `security_tests` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 46 | `simulations` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | High | Required | Yes | Subquery join via `agents` | Medium |
| 47 | `transactions` | `id` | ❌ | ❌ | Child via Agent | `agent_id->agents.org_id` | Critical | Required | Yes | Subquery join via `agents` | Medium |
| 48 | `sessions` | `id` | ❌ | ✅ | Child via User | `user_id->users.org_id` | Critical | Required | Yes | Subquery join via `users` | Medium |
| 49 | `notifications` | `id` | ❌ | ✅ | Child via User | `user_id->users.org_id` | Medium | Required | Yes | Subquery join via `users` | Medium |
| 50 | `webhook_deliveries` | `id` | ❌ | ❌ | Child via Webhook | `webhook_id->webhook_endpoints.org_id` | Medium | Required | Yes | Subquery join via `webhook_endpoints` | Medium |

---

## Global System / Catalog Tables (Not Tenant-Specific)

| Table Name | Primary Key | Purpose | RLS Status | Access Policy |
|---|---|---|---|---|
| `plans` | `id` | Subscription tiers (Free, Starter, Pro, Enterprise) | Enabled | SELECT to `authenticated`; Write restricted to `service_role` / `super_admin` |
| `ai_models` | `id` | Supported LLM catalogs, latency, costs | Enabled | SELECT to `authenticated`; Write restricted to `service_role` / `super_admin` |
| `capabilities` | `id` | Capability registry (resource, action, max_amount) | Enabled | SELECT to `authenticated`; Write restricted to `service_role` / `super_admin` |
| `model_pricing` | `id` | Pricing matrix for token input/output | Enabled | SELECT to `authenticated`; Write restricted to `service_role` / `super_admin` |
| `policy_rules` | `id` | AST policy condition definitions | Enabled | Filtered via parent `policies.org_id` join |
| `otp_challenges` | `id` | Temporary authentication challenge tokens | Enabled | PostgREST revoked; Managed exclusively by backend `service_role` |

---

## Key Risk Takeaways & Architectural Recommendations

1. **Tables Requiring Subquery Policies (19 tables)**:
   - Tables without a direct `org_id` column (e.g. `decisions`, `approval_requests`, `capability_tokens`, `sessions`) depend on subqueries to resolve tenant boundaries.
   - *Performance Recommendation*: In high-throughput tables (`decisions`, `agent_executions`, `capability_tokens`), ensure foreign key columns (`agent_id`, `user_id`) possess B-tree indexes.
   - *Future Schema Optimization*: Adding a denormalized, indexed `org_id` column to `decisions` and `approval_requests` simplifies policies from correlated subqueries to simple direct equality (`org_id = current_org_id()`), drastically reducing query planning overhead.
2. **PostgREST Lockdown**:
   - `anon` access to all application tables is completely revoked.
   - Pre-authentication tables like `otp_challenges` are isolated entirely from client PostgREST roles.
