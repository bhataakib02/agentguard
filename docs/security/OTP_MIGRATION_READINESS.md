# AGENTGUARD — OTP Challenges Migration Readiness Report

**Document Version**: 1.0.0  
**Target Table**: `public.otp_challenges`  
**Related Revisions**: Alembic `0002_add_otp_challenges`, Supabase `20261022000000_add_otp_challenges_table.sql`  
**Status**: Table Pre-Deployed and Verified in Live Database  

---

## 1. Executive Summary

A deep read-only inspection of the live PostgreSQL database (`xjragvyzlailmtfwjfnm`) revealed that `public.otp_challenges` **already exists** in production. It was provisioned via Supabase SQL migration `20261022000000_add_otp_challenges_table.sql`.

This report provides the full verification results comparing the live `otp_challenges` schema against the SQLAlchemy model `OtpChallenge` (`backend/models.py`) and Alembic revision `0002_add_otp_challenges` (`backend/alembic/versions/0002_add_otp_challenges_table.py`).

---

## 2. Column Specification & Parity Verification

| Column Name | Live DB Data Type | Model / Alembic Type | Nullable | Default | Match Status | Security Function |
|---|---|---|---|---|---|---|
| `id` | `uuid` | `models.GUID` / `UUID` | **NO** | `gen_random_uuid()` | **MATCH** | Surrogate Primary Key |
| `email` | `character varying` | `String` | **NO** | None | **MATCH** | Destination Identity |
| `purpose` | `character varying` | `String` | **NO** | None | **MATCH** | Context (`REGISTRATION`, `PASSWORD_RESET`, `STEP_UP`) |
| `code_hash` | `character varying` | `String` | **NO** | None | **MATCH** | Cryptographic HMAC-SHA256 of OTP |
| `attempts` | `integer` | `Integer` | **NO** | `0` | **MATCH** | Failed verification attempt counter |
| `max_attempts` | `integer` | `Integer` | **NO** | `5` | **MATCH** | Threshold limit before challenge invalidation |
| `consumed` | `boolean` | `Boolean` | **NO** | `false` | **MATCH** | Replay prevention flag |
| `consumed_at` | `timestamp with time zone`| `DateTime(timezone=True)`| YES | None | **MATCH** | Consumption audit timestamp |
| `expires_at` | `timestamp with time zone`| `DateTime(timezone=True)`| **NO** | None | **MATCH** | Strict TTL expiration boundary (typically 10 min) |
| `resend_available_at`| `timestamp with time zone`| `DateTime(timezone=True)`| **NO** | None | **MATCH** | Cooldown throttle boundary (120 seconds) |
| `ip_address` | `character varying` | `String` | YES | None | **MATCH** | Request IP telemetry & rate-limiting key |
| `metadata_json`| `jsonb` | `JSON` | YES | `'{}'::jsonb` | **MATCH** | Encrypted metadata / registration payload |
| `created_at` | `timestamp with time zone`| `DateTime(timezone=True)`| YES | `now()` | **MATCH** | Record creation timestamp |

---

## 3. B-Tree Index Definitions

Catalog introspection confirms all 6 required B-Tree indexes exist with exact column bounds:

```sql
-- Primary Key
CREATE UNIQUE INDEX otp_challenges_pkey ON public.otp_challenges USING btree (id);

-- Lookup and Verification Indexes
CREATE INDEX ix_otp_challenges_email ON public.otp_challenges USING btree (email);
CREATE INDEX ix_otp_challenges_purpose ON public.otp_challenges USING btree (purpose);
CREATE INDEX ix_otp_challenges_code_hash ON public.otp_challenges USING btree (code_hash);
CREATE INDEX ix_otp_challenges_consumed ON public.otp_challenges USING btree (consumed);
CREATE INDEX ix_otp_challenges_expires_at ON public.otp_challenges USING btree (expires_at);
CREATE INDEX ix_otp_challenges_created_at ON public.otp_challenges USING btree (created_at);
```

---

## 4. Security & PostgREST Access Hardening

1. **Pre-Authentication Isolation**:
   - `otp_challenges` stores sensitive verification hashes, rate-limiting metadata, and temporary registration payloads.
   - It must **never** be accessible to `anon` or `authenticated` roles via PostgREST.
   - In the live database, `anon` and `authenticated` currently have no `SELECT` or `INSERT` privileges.
   - Under the defense-in-depth RLS migration:
     ```sql
     ALTER TABLE public.otp_challenges ENABLE ROW LEVEL SECURITY;
     DROP POLICY IF EXISTS service_role_all ON public.otp_challenges;
     CREATE POLICY service_role_all ON public.otp_challenges FOR ALL TO service_role USING (true) WITH CHECK (true);
     REVOKE ALL ON public.otp_challenges FROM anon, authenticated;
     ```
2. **HMAC Storage Security**:
   - OTP codes are never stored in plaintext. `code_hash` is computed as `hmac_sha256(secret_key, code + salt)`.
3. **Background Cleanup Compatibility**:
   - The Celery worker task `tasks.otp_tasks.purge_expired_otp_challenges` queries `expires_at < now() - interval '24 hours'` or `consumed = true`.
   - The composite index coverage (`ix_otp_challenges_expires_at` and `ix_otp_challenges_consumed`) guarantees linear-time deletion scans without full-table locks.

---

## 5. Migration Execution Decision

- **DDL Execution Required**: **NO**. The table and indexes are already deployed.
- **Alembic Action Required**: When Alembic baseline reconciliation is approved, running `alembic stamp 0002_add_otp_challenges` (or running `0001` stamp followed by `0002` upgrade) will adopt the table idempotently without executing duplicate `CREATE TABLE` DDL.
