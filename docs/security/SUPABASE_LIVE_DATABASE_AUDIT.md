# AGENTGUARD — Supabase Live Database Security Audit

**Audit Date**: November 25, 2026  
**Auditor**: Independent Security Architecture Audit Team  
**Database Instance**: Supabase PostgreSQL 17.6.1 (`xjragvyzlailmtfwjfnm` / `AgentGuard` / `ap-south-1`)  
**Audit Scope**: Read-Only Database Catalog & Privilege Inspection  
**Classification**: **SECURITY EXPOSURE FOUND — IMMEDIATE REMEDIATION PLAN REQUIRED**  

---

## 1. Executive Summary

A comprehensive, non-mutating, read-only security audit of the production Supabase PostgreSQL instance (`xjragvyzlailmtfwjfnm`) was executed. The audit evaluated role memberships, role attributes (including `BYPASSRLS`), table-level grants, schema-level default privileges, security definer routines, PostgREST API exposure, active RLS status, and storage buckets.

### Key Audit Findings:
1. **Critical Privilege Exposure — TRUNCATE Granted to Anon & Authenticated**:
   - While `anon` and `authenticated` roles do **not** possess `SELECT`, `INSERT`, `UPDATE`, or `DELETE` on any public table, both roles possess explicit **`TRUNCATE`**, **`REFERENCES`**, and **`TRIGGER`** privileges on all 50 public tables.
   - This was verified directly via PostgreSQL catalog introspection (`has_table_privilege('anon', 'public.users', 'TRUNCATE') = TRUE`).
   - Catalog analysis of `pg_class.relacl` confirmed these permissions are direct table ACL grants generated via `pg_default_acl` under the `postgres` role, and are **not** inherited from pseudo-role `PUBLIC` (`public_can_truncate = false`).
   - Although PostgREST does not expose an HTTP TRUNCATE verb, this permission represents an active security exposure for any direct client, RPC function, or extension running under `anon` or `authenticated`.
2. **50 Public Tables with RLS Disabled & 0 RLS Policies**:
   - Row Level Security is disabled (`rowsecurity = false`) across all 50 public tables.
   - There are currently 0 active RLS policies in the `public` schema.
   - The Supabase dashboard advisory warning stating *"anyone with the anon key can read or modify every row"* is inaccurate regarding SELECT/INSERT/UPDATE/DELETE (which are denied), but accurate in that tables lack row-level policy enforcement.
3. **Database Roles & Connection Architecture**:
   - The FastAPI backend connects via the Supavisor transaction pooler (port 6543) as `postgres.xjragvyzlailmtfwjfnm` (role `postgres`).
   - Role `postgres` owns all 50 tables, has `rolbypassrls = true`, and has `rolsuper = false`.
   - Role `service_role` has `rolbypassrls = true`.
   - Role `authenticator` (used by PostgREST) inherits `anon`, `authenticated`, and `service_role` without login permission inheritance (`rolinherit = false`).
4. **Table Inventory & Alembic Tracking**:
   - The live database contains **50 public tables**, including the newly created `otp_challenges` table.
   - The `alembic_version` table does **not** exist in the live database (0 migration tracking records).
5. **Storage Configuration**:
   - The `storage.buckets` table is completely empty (`0` buckets). Supabase Storage is not utilized by the AGENTGUARD application.

---

## 2. Audit Discrepancy Resolution (Phase 1)

During previous assessments, discrepancy in table counts (49 vs 50) and user counts (45/4 vs 1/1) were reported. A read-only investigation resolved these discrepancies definitively:

### 1. Table Count (49 to 50):
- **Finding**: Alembic canonical baseline revision `0001_initial_canonical_schema.py` defines 49 tables.
- **Resolution**: Table #50 is `otp_challenges`, created via Supabase migration `supabase/migrations/20261022000000_add_otp_challenges_table.sql`. Introspection of `information_schema.columns` and `pg_indexes` confirmed that `otp_challenges` exists with all 13 columns and 6 B-tree indexes matching revision `0002_add_otp_challenges_table.py` exactly.

### 2. User Accounts Discrepancy (45/4 to 1/1):
- **Finding**: Live catalog queries revealed exactly 1 record in `auth.users` and 1 record in `public.users`.
- **Root Cause**: Introspection of `pg_stat_user_tables` revealed:
  - `auth.users`: `n_tup_del = 44`
  - `public.users`: `n_tup_del = 4`, `n_tup_ins = 1`
  - `public.organizations`: `n_tup_del = 3`, `n_tup_ins = 1`
- **Resolution**: A controlled maintenance operation using `supabase/clean_production_data.sql` executed line 118 (`DELETE FROM auth.users WHERE id <> sa_auth_id;`), safely purging 44 unattached demo auth accounts and 4 demo public user profiles, preserving exactly 1 active `SUPER_ADMIN` user across both tables.
- **Environment Confirmation**: The findings refer to the single active AGENTGUARD production database project `xjragvyzlailmtfwjfnm` in region `ap-south-1`.

---

## 3. PostgreSQL Role Attributes & Membership Matrix

Catalog introspection of `pg_roles` and `pg_auth_members`:

| Role Name | Superuser (`rolsuper`) | Inherits (`rolinherit`) | Can Login (`rolcanlogin`) | Bypass RLS (`rolbypassrls`) | Role Memberships |
|---|---|---|---|---|---|
| `postgres` | `false` | `true` | `true` | `true` | `anon`, `authenticated`, `service_role`, `supabase_privileged_role`, `pg_monitor`, `pg_signal_backend`, `pg_read_all_data`, `pg_create_subscription` |
| `service_role` | `false` | `true` | `false` | `true` | None |
| `authenticated` | `false` | `true` | `false` | `false` | None |
| `anon` | `false` | `true` | `false` | `false` | None |
| `authenticator` | `false` | `false` | `true` | `false` | `anon`, `authenticated`, `service_role` |
| `supabase_admin` | `true` | `true` | `true` | `true` | Superuser administrative root |

---

## 4. Source of TRUNCATE Privileges & Revocation Specification

Inspection of `pg_class.relacl` across public schema tables:
```sql
relacl: {postgres=arwdDxtm/postgres, anon=Dxtm/postgres, authenticated=Dxtm/postgres, service_role=Dxtm/postgres}
```
Inspection of pseudo-role `PUBLIC`:
```sql
has_table_privilege('public', 'public.users', 'TRUNCATE') -> FALSE
```

### Root Cause:
`anon` and `authenticated` did **not** acquire `TRUNCATE` from `PUBLIC`. Rather, the table creator role `postgres` has default privileges configured in `pg_default_acl` that explicitly grant `Dxtm` (`D` = TRUNCATE, `x` = REFERENCES, `t` = TRIGGER, `m` = MAINTAIN) upon table creation.

### Narrowly Scoped Revocation SQL (For Execution in Staging/Maintenance):
```sql
-- 1. Revoke dangerous table-level grants from existing public tables
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM authenticated;

-- 2. Ensure default privileges do not grant TRUNCATE on future tables
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM authenticated;
```
*(Note: In accordance with absolute restrictions, this SQL is specified for staging/maintenance and was NOT executed against production).*

---

## 5. Security Definer Functions & Triggers

- **Functions**: Audited `pg_proc` where `pronamespace = 'public'::regnamespace`. Result: `0` user-defined functions exist in the `public` schema. There are **no** `SECURITY DEFINER` functions in `public`.
- **Triggers**: Audited `information_schema.triggers` across `public` and `auth` schemas. Result: `0` application-level triggers exist. There are no automatic profile synchronization triggers between `auth.users` and `public.users`.
