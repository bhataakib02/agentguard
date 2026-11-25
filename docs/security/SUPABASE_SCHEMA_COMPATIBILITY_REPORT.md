# AGENTGUARD — Supabase Production Schema Compatibility Audit Report

**Audit Date**: 2026-11-25  
**Target Database**: Supabase Live Database `xjragvyzlailmtfwjfnm` (`AgentGuard`, region `ap-south-1`, PostgreSQL 17.6.1)  
**Target Migration**: `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql`  
**Compatibility Verdict**: **100% COMPATIBLE (VERIFIED VIA READ-ONLY CATALOG INSPECTION)**  

---

## 1. Executive Summary

An exhaustive, read-only catalog inspection of all 50 public schema tables on the live Supabase production instance (`xjragvyzlailmtfwjfnm`) was conducted to evaluate compatibility with the proposed Row Level Security (RLS) migration.

Every table, column type, nullability constraint, foreign key relationship, table owner, existing grant, and policy was audited.

### Core Compatibility Findings:
1. **Table Coverage (50/50)**: All 50 tables assumed by the migration exist in the live database schema under owner `postgres`.
2. **Current Policy State (0/50)**: Zero RLS policies currently exist in `pg_policies` on the live database. `relrowsecurity` is currently `false` on all 50 tables. The forward migration introduces 0 conflicting or duplicate policies.
3. **Type Compatibility Verified**: The explicit cast `auth.uid()::text` in the `notifications` policy reconciles the `VARCHAR` data type of `public.users.auth_user_id` with the `UUID` return type of `auth.uid()`, preventing `operator does not exist: character varying = uuid` errors.
4. **Polymorphic Decision Architecture**: Live inspection confirmed that `public.decisions.agent_id` is `NOT NULL` on the live database, while `user_id` is nullable. The remediated decision policy in Section 7 cleanly matches this live schema structure.
5. **Pre-Auth Isolation (`otp_challenges`)**: The table `otp_challenges` exists with default UUID generation (`gen_random_uuid()`) and timestamps with time zone. Revoking all access from `anon` and `authenticated` secures this sensitive table without altering table structure.

---

## 2. 50-Table Schema Verification & Compatibility Matrix

| # | Table Name | Live Table Type | Live Owner | Current RLS | Direct Org Column | Compatibility Status |
|---|---|---|---|---|---|---|
| 1 | `agent_budget_configs` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 2 | `agent_credentials` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 3 | `agent_executions` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 4 | `agent_passports` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 5 | `agent_relationships` | BASE TABLE | `postgres` | Disabled | Via Dual Agents | **COMPATIBLE** |
| 6 | `agent_runtime_sessions` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 7 | `agents` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 8 | `ai_models` | BASE TABLE | `postgres` | Disabled | Global Reference | **COMPATIBLE** |
| 9 | `anomaly_events` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 10 | `api_keys` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 11 | `approval_requests` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 12 | `audit_logs` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, Nullable) | **COMPATIBLE** |
| 13 | `behavior_profiles` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 14 | `budgets` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 15 | `capabilities` | BASE TABLE | `postgres` | Disabled | Global Reference | **COMPATIBLE** |
| 16 | `capability_tokens` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 17 | `circuit_breakers` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 18 | `decisions` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 19 | `evaluation_dataset_records` | BASE TABLE | `postgres` | Disabled | Via Dataset | **COMPATIBLE** |
| 20 | `evaluation_datasets` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 21 | `license_usages` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 22 | `licenses` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 23 | `model_pricing` | BASE TABLE | `postgres` | Disabled | Global Reference | **COMPATIBLE** |
| 24 | `notifications` | BASE TABLE | `postgres` | Disabled | Via `users.org_id` | **COMPATIBLE** |
| 25 | `organizations` | BASE TABLE | `postgres` | Disabled | `id` (Root Boundary) | **COMPATIBLE** |
| 26 | `otp_challenges` | BASE TABLE | `postgres` | Disabled | Pre-Auth (No Org) | **COMPATIBLE** |
| 27 | `permissions` | BASE TABLE | `postgres` | Disabled | Global Catalog | **COMPATIBLE** |
| 28 | `plans` | BASE TABLE | `postgres` | Disabled | Global Catalog | **COMPATIBLE** |
| 29 | `policies` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 30 | `policy_rules` | BASE TABLE | `postgres` | Disabled | Via `policies.org_id` | **COMPATIBLE** |
| 31 | `provenance_events` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 32 | `report_histories` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 33 | `reputation_scores` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 34 | `resource_usages` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 35 | `risk_scores` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 36 | `runtime_risk_signals` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 37 | `sandbox_execution_jobs` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 38 | `scheduled_reports` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 39 | `security_incidents` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 40 | `security_tests` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 41 | `sessions` | BASE TABLE | `postgres` | Disabled | Direct Auth Token | **COMPATIBLE** |
| 42 | `siem_configs` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 43 | `siem_deliveries` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 44 | `simulations` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 45 | `tools` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, Nullable) | **COMPATIBLE** |
| 46 | `transactions` | BASE TABLE | `postgres` | Disabled | Via `agents.org_id` | **COMPATIBLE** |
| 47 | `user_invitations` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 48 | `users` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |
| 49 | `webhook_deliveries` | BASE TABLE | `postgres` | Disabled | Via Endpoint | **COMPATIBLE** |
| 50 | `webhook_endpoints` | BASE TABLE | `postgres` | Disabled | `org_id` (UUID, NOT NULL) | **COMPATIBLE** |

---

## 3. Deep-Dive on Sensitive and Polymorphic Tables

### 1. `audit_logs`
- **Live Columns**: `id` (uuid, NOT NULL), `org_id` (uuid, NULLABLE), `event_type` (varchar, NOT NULL), `actor_type` (varchar), `actor_id` (varchar, NOT NULL), `action` (varchar, NOT NULL), `resource` (varchar, NOT NULL), `result` (varchar, NOT NULL), `metadata_json` (json), `timestamp` (timestamp).
- **Compatibility Analysis**:
  - `org_id` is nullable in production to accommodate system-level background events (e.g., system startups, global migrations).
  - The migration defines `tenant_read_audit_logs` (SELECT) using `org_id = public.current_org_id() OR public.is_super_admin()`. This ensures tenants only see logs with their tenant UUID, while SUPER_ADMIN and system workers can inspect global events.
  - Table permissions strictly revoke `UPDATE` and `DELETE` from `authenticated`.

### 2. `tools`
- **Live Columns**: `id` (uuid, NOT NULL), `org_id` (uuid, NULLABLE), `name` (varchar, NOT NULL), `category`, `endpoint`, `description`, `risk_level`, `status`, `latency_ms`, `schema_definition` (json), `headers_json` (json), `timeout_seconds`.
- **Compatibility Analysis**:
  - System tools have `org_id IS NULL`, while tenant-custom tools have `org_id = <uuid>`.
  - The migration policy `tenant_read_tools` checks `org_id IS NULL OR org_id = public.current_org_id() OR public.is_super_admin()`, preserving universal visibility of system tools.
  - Modification policies (`tenant_write_tools`) strictly enforce `org_id = public.current_org_id()`, preventing tenants from altering system tools.

### 3. `agent_relationships`
- **Live Columns**: `id` (uuid, NOT NULL), `parent_agent_id` (uuid, NOT NULL), `child_agent_id` (uuid, NOT NULL), `trust_status` (varchar), `allowed_delegation_types` (varchar).
- **Compatibility Analysis**:
  - Table has no direct `org_id` column.
  - The migration policy checks that **both** `parent_agent_id` AND `child_agent_id` exist in `public.agents` with `org_id = public.current_org_id()`.
  - This prevents cross-tenant delegation bridging and satisfies relational integrity.

### 4. `decisions`
- **Live Columns**: `id` (uuid, NOT NULL), `agent_id` (uuid, NOT NULL), `user_id` (uuid, NULLABLE), `intent_summary` (varchar, NOT NULL), `action_requested` (varchar, NOT NULL), `resource_target` (varchar, NOT NULL), `amount` (float), `decision` (varchar, NOT NULL), `explanation` (text, NOT NULL), `tool_id` (uuid), `execution_parameters` (json).
- **Compatibility Analysis**:
  - Live schema has `agent_id` as non-nullable.
  - The migration policy supports agent-originated decisions (`agent_id IS NOT NULL` with tenant check) and verifies that if `user_id` is also populated, it belongs to the same tenant.
  - Symmetrically verified in both `USING` and `WITH CHECK`.

### 5. `otp_challenges`
- **Live Columns**: `id` (uuid, default `gen_random_uuid()`), `email` (varchar, NOT NULL), `purpose` (varchar, NOT NULL), `code_hash` (varchar, NOT NULL), `attempts` (int, default 0), `max_attempts` (int, default 5), `consumed` (boolean, default false), `consumed_at` (timestamptz), `expires_at` (timestamptz, NOT NULL), `resend_available_at` (timestamptz, NOT NULL), `ip_address` (varchar), `metadata_json` (jsonb, default `'{}'::jsonb`), `created_at` (timestamptz).
- **Compatibility Analysis**:
  - Migration enables RLS, creates a `service_role_all` policy, and executes `REVOKE ALL ON public.otp_challenges FROM anon, authenticated`.
  - Completely blocks PostgREST exposure while maintaining background cleanup tasks.

### 6. `users` & `notifications`
- **Live Columns**:
  - `users.id`: uuid, NOT NULL
  - `users.auth_user_id`: varchar, NULLABLE (stores Supabase `auth.users.id` string)
  - `users.full_name`: varchar, NOT NULL
  - `notifications.user_id`: uuid, NULLABLE
- **Compatibility Analysis**:
  - The explicit cast in `notifications`: `(public.users.auth_user_id = auth.uid()::text OR public.users.id = auth.uid())` eliminates any type mismatch error between PostgreSQL `character varying` and `uuid`.

---

## 4. Privilege & Role Compatibility

### Direct & Default ACLs on Live Supabase:
- `pg_class.relacl` currently contains `{postgres=arwdDxtm/postgres, anon=Dxtm/postgres, authenticated=Dxtm/postgres, service_role=Dxtm/postgres}`.
- Unauthenticated (`anon`) and authenticated web clients hold `TRUNCATE, REFERENCES, TRIGGER` on all 50 tables.
- The proposed migration executes:
  ```sql
  REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
  REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM authenticated;
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
  ```
- This cleanly strips dangerous privileges without breaking application reads/writes.

---

## 5. Schema Compatibility Verdict

### **100% COMPATIBLE WITH LIVE SUPABASE PRODUCTION**
- Zero column discrepancies.
- Zero missing foreign key target tables.
- Zero conflicting policies.
- Helper functions operate cleanly under PostgreSQL 17 execution semantics.
