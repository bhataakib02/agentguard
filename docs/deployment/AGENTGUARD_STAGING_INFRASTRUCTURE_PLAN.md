# AGENTGUARD — Isolated Staging Infrastructure Readiness & Provisioning Plan

**Document Reference**: AGENTGUARD-STAGING-PLAN-2026-11-28  
**Release Gate Association**: Post-Security Audit Pre-Production Staging Gate  
**Classification**: Enterprise Infrastructure Architecture & Deployment Planning  
**Execution Status**: **PREPARATION & AUDIT ONLY** (Zero external resources provisioned; production completely untouched)  

---

## 1. Executive Summary & Objective

Following the official **AGENTGUARD Pre-Production Security Release Gate**, the security audit established a **CONDITIONAL GO** rating, permitting deployment exclusively to an **isolated staging environment** while holding production release pending live verification.

This document defines the comprehensive blueprint for provisioning, configuring, isolating, and validating AGENTGUARD's dedicated staging environment.

### Core Isolation Mandates
1. **Zero Resource Sharing**: Staging must never share PostgreSQL databases, Redis instances, JWT signing keys, AES master encryption keys, Supabase projects, or cloud credentials with production.
2. **Zero Blast Radius**: Any failure, load test, penetration test, database migration rehearsal, or schema rollback in staging must have zero impact on production operations or data.
3. **Parity with Production**: Staging must replicate production architecture (FastAPI backend, Next.js frontend, Supabase PostgreSQL 15+, Redis-backed Celery workers, and Celery Beat scheduler) to guarantee high-fidelity security and performance validation.

---

## 2. Audit of Existing Configuration & Staging Gaps

An exhaustive audit of the existing codebase, deployment definitions, and configuration files was conducted:

| Configuration Artifact | Current State / Definition | Identified Staging Gaps / Deficiencies | Action Required for Staging |
|---|---|---|---|
| **`render.yaml`** | Declares production service group (`agentguard-shared`) and 4 services: `agentguard-backend` (web), `agentguard-worker` (celery), `agentguard-beat` (scheduler), `agentguard-redis` (keyvalue). | Single production environment defined; no `staging` service group or environment variable definitions exist. | Create dedicated Staging Render Blueprint or separate staging services with `-staging` suffix. |
| **`docker-compose.yml`** | Defines local development stack: `redis:7-alpine`, `api`, `worker`, `beat`. | Geared for local developer workstations; not suitable for remote cloud staging. | Retain for local dev; maintain cloud parity via Render staging. |
| **`docker-compose.staging.yml`** | Defines `staging-postgres` (PostgreSQL 16 on `127.0.0.1:5433`) and `staging-redis` (Redis 7 on `127.0.0.1:6380`). | Suitable for local offline integration testing; cannot replace remote cloud Supabase staging. | Use as local containerized staging drill harness; provision cloud staging for UAT. |
| **`vercel.json`** | Defines build and output directories for Next.js (`frontend/.next`). | Single production project deployment; no isolated staging preview domain or environment mappings. | Configure Vercel Staging Environment with dedicated preview domain (e.g. `staging.agentguard.io`). |
| **`backend/config.py`** | Enforces production validations (`ENVIRONMENT == "production"` requires >=32 char `SECRET_KEY`, non-SQLite `DATABASE_URL`, disables local login). | `ENVIRONMENT=staging` needs to mirror production constraints while allowing staging email providers and test seeds. | Set `ENVIRONMENT=staging` with production parity flags enabled. |
| **`backend/database.py`** | Contains `validate_test_database_target` to abort tests if pointing to non-test databases. | Guard validates `testing` environment; must ensure staging connection strings are never confused with production. | Ensure distinct hostnames for staging (`*.supabase.co` project ref must differ from `xjragvyzlailmtfwjfnm`). |
| **Alembic (`backend/alembic/`)** | Two versions: `0001_initial_canonical_schema.py` and `0002_add_otp_challenges_table.py`. | Unstamped on new databases; requires clean baseline execution. | Run `alembic upgrade head` on fresh staging DB before applying RLS. |
| **Supabase Project** | Production project `xjragvyzlailmtfwjfnm` exists and is active. | **No dedicated Supabase staging project exists.** Using production as staging is strictly prohibited. | Provision dedicated Supabase project: `agentguard-staging`. |
| **Redis & Celery** | Celery tasks fall back to eager mode (`CELERY_TASK_ALWAYS_EAGER=True`) if `REDIS_URL` is empty. | Multi-pod worker validation requires live Redis broker in staging. | Provision dedicated managed Redis instance on Render (`agentguard-redis-staging`). |
| **Email Delivery** | `config.py` defaults to `onboarding@resend.dev` (sandbox). | Rejects external recipient emails in production/staging. | Configure staging-specific email sandbox with whitelisted recipient domains. |

---

## 3. Dedicated Staging Architecture & Trust Boundaries

The staging environment replicates the complete production microservice topology in an isolated, sandboxed environment:

```
[ Staging User / QA Engineer ]           [ Staging Autonomous AI Agent ]
              │                                        │
              ▼ (HTTPS / WSS)                          ▼ (Bearer Staging Machine JWT)
┌─────────────────────────────────────────────────────────────────────────┐
│               STAGING FRONTEND (Vercel Preview / Staging)              │
│  - Domain: https://staging.agentguard.io                                │
│  - Environment: NEXT_PUBLIC_API_URL=https://staging-api.agentguard.io   │
│  - Edge Middleware: Staging route protection & session verification     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼ (HTTPS / REST)
┌─────────────────────────────────────────────────────────────────────────┐
│               STAGING BACKEND API (Render Web Service)                  │
│  - Service Name: agentguard-backend-staging                             │
│  - Domain: https://staging-api.agentguard.io                            │
│  - Runtime: Python 3.10 / FastAPI / Uvicorn                             │
│  - Config: ENVIRONMENT=staging                                          │
│  - Zero Shared State with Production                                    │
└──────────────┬─────────────────────┬─────────────────────┬──────────────┘
               │                     │                     │
               ▼                     ▼                     ▼
┌──────────────────────────┐ ┌──────────────────┐ ┌───────────────────────┐
│ STAGING SUPABASE PG 15+  │ │  STAGING REDIS   │ │ STAGING EMAIL SANDBOX │
│ - Dedicated Project Ref  │ │ - Dedicated Node │ │ - Resend Staging Sub- │
│ - 50 Tables Initialized  │ │ - Render KV      │ │   account or Brevo    │
│ - Full RLS Defense-in-   │ │ - Celery Broker  │ │ - Whitelisted Tester  │
│   Depth Policies Applied │ │ - Result Backend │ │   Recipients Only     │
│ - PostgREST Hardened     │ │ - Distributed RL │ │ - Zero Real Customer  │
└──────────────────────────┘ └─────────┬────────┘ │   Dispatches          │
                                       │          └───────────────────────┘
                              ┌────────┴────────┐
                              ▼                 ▼
                     ┌─────────────────┐ ┌───────────────┐
                     │ STAGING WORKER  │ │ STAGING BEAT  │
                     │ - Celery Worker │ │ - Celery Beat │
                     │ - 4 Concurrency │ │ - 1 Instance  │
                     └─────────────────┘ └───────────────┘
```

### Trust Boundary Analysis:
1. **Network Boundary**: Staging services operate on isolated virtual private networks and subnets. Staging backend only connects to Staging PostgreSQL and Staging Redis.
2. **Data Boundary**: Staging database is populated with synthetic demonstration organizations and test agents. No production PII, real customer credentials, or production audit logs are ever copied into staging.
3. **Identity Boundary**: Staging uses a completely independent Supabase Auth instance. User accounts created in staging do not exist in production.
4. **Cryptographic Boundary**: Staging utilizes freshly generated 64-character cryptographic secrets (`SECRET_KEY`, `LOCAL_AES_MASTER_KEY`). Ciphertexts encrypted in staging cannot be decrypted by production, and vice versa.

---

## 4. Staging Component Specifications

### 1. Staging Frontend
- **Hosting Provider**: Vercel
- **Project Link**: Separate Vercel project or dedicated `staging` Git branch deployment.
- **Custom Domain**: `staging.agentguard.io` (or `agentguard-staging.vercel.app`)
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL=https://staging-api.agentguard.io/api`
  - `NEXT_PUBLIC_WS_URL=wss://staging-api.agentguard.io/ws`
  - `NEXT_PUBLIC_SUPABASE_URL=https://[STAGING-PROJECT-ID].supabase.co`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY=[STAGING-SUPABASE-ANON-KEY]`

### 2. Staging FastAPI Backend
- **Hosting Provider**: Render
- **Service Name**: `agentguard-backend-staging`
- **Region**: `singapore` (or `oregon` matching staging database)
- **Instance Type**: `starter` (0.5 CPU, 512 MB RAM)
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT --ws-ping-interval 20 --ws-ping-timeout 20`
- **Health Check Path**: `/health/ready`

### 3. Staging PostgreSQL / Supabase
- **Hosting Provider**: Supabase Managed Database
- **Project Name**: `AgentGuard-Staging`
- **Region**: Matching backend region for low network latency.
- **PostgreSQL Version**: 15+ / 17.x (matching production engine).
- **Extensions**: `pgcrypto`, `uuid-ossp`.
- **Connection Configuration**:
  - Direct connection (Port 5432) for Alembic migrations and DDL.
  - Transaction connection pooler (Port 6543 / Supavisor) for FastAPI runtime backend.

### 4. Staging Redis
- **Hosting Provider**: Render KeyValue / Redis
- **Service Name**: `agentguard-redis-staging`
- **Plan**: `starter`
- **Max Memory Policy**: `noeviction`

### 5. Staging Celery Worker
- **Hosting Provider**: Render Background Worker
- **Service Name**: `agentguard-worker-staging`
- **Start Command**: `celery -A celery_app.celery_app worker --loglevel=info --concurrency=4 -Q celery`

### 6. Staging Celery Beat
- **Hosting Provider**: Render Background Worker
- **Service Name**: `agentguard-beat-staging`
- **Start Command**: `celery -A celery_app.celery_app beat --loglevel=info`
- **Instances**: Strictly 1 instance (to avoid duplicate periodic task triggers).

---

## 5. Staging Email Configuration & Safety Guardrails

To prevent accidental email leakage or spamming real users from staging:

### Safety Guardrails:
1. **Isolated Provider API Key**: Staging must never use the production Brevo or Resend API key.
2. **Recipient Whitelisting**: Staging email configuration must enforce a recipient domain whitelist:
   - Allowed: `@agentguard.internal`, `@agentguard.io`, and registered staging QA testers.
   - Prohibited: External personal or enterprise domains not explicitly whitelisted.
3. **Safe Fallback**: If dedicated staging email credentials are not provisioned, staging will run with `EMAIL_PROVIDER=MOCK` or `EMAIL_PROVIDER=NONE`, where OTP codes and invitation links are logged to application audit logs (`models.AuditLog`) for tester retrieval without external network dispatch.

---

## 6. Staging Deployment Checklist

Follow this exhaustive checklist during the staging provisioning and deployment window:

### Step 1: Pre-Provisioning & Authorization
- [ ] Explicit user authorization granted for staging resource creation.
- [ ] Staging project naming convention established (`agentguard-*-staging`).
- [ ] Clean staging branch identified (`staging` branched from `main` @ `5e8523e`).

### Step 2: Supabase Staging Database Provisioning
- [ ] Create dedicated Supabase project `AgentGuard-Staging`.
- [ ] Record staging project reference, API URL, publishable key, service role key, and database connection strings.
- [ ] Enable `pgcrypto` and `uuid-ossp` extensions in staging database.
- [ ] Verify database connectivity via `psql "$STAGING_DATABASE_URL" -c "SELECT version();"`.

### Step 3: Redis & Worker Infrastructure Provisioning
- [ ] Create Render Redis instance `agentguard-redis-staging`.
- [ ] Copy staging `REDIS_URL` connection string.
- [ ] Create Render Web Service `agentguard-backend-staging`.
- [ ] Create Render Worker `agentguard-worker-staging`.
- [ ] Create Render Beat Worker `agentguard-beat-staging`.

### Step 4: Secret Generation & Environment Configuration
- [ ] Generate unique 64-char hex `SECRET_KEY` for staging.
- [ ] Generate unique 64-char hex `LOCAL_AES_MASTER_KEY` for staging.
- [ ] Populate staging environment variables in Render Dashboard (see `AGENTGUARD_STAGING_ENVIRONMENT_VARIABLES.md`).
- [ ] Configure Vercel staging environment variables for frontend.

### Step 5: Database Schema & Baseline Migration
- [ ] Execute Alembic migrations on staging: `alembic upgrade head`.
- [ ] Verify all 50 tables are created in public schema.
- [ ] Seed canonical license plans via `python backend/bootstrap.py --seed-plans`.

### Step 6: Defense-in-Depth RLS Migration & Hardening
- [ ] Follow `AGENTGUARD_STAGING_RLS_MIGRATION_RUNBOOK.md` step-by-step.
- [ ] Execute `20261125010000_idempotent_defense_in_depth_rls.sql` in staging.
- [ ] Verify 50 tables have `rowsecurity = true`.
- [ ] Verify privilege revocation (`TRUNCATE`, `REFERENCES`, `TRIGGER` revoked from `anon` and `authenticated`).

### Step 7: Staging Automated Test & Verification Suite
- [ ] Run live RLS test suite: `POSTGRES_TEST_URL="$STAGING_DATABASE_URL" python -m pytest backend/tests/test_postgresql_rls_validation.py -v`.
- [ ] Run full regression suite against staging backend.
- [ ] Verify `/health/live` returns HTTP 200 `ALIVE`.
- [ ] Verify `/health/ready` returns HTTP 200 `READY`.
- [ ] Verify `/platform/health` returns accurate staging subsystem statuses.

### Step 8: Multi-Tenant & Governance Smoke Tests
- [ ] Register Test Organization A and verify OTP delivery / retrieval.
- [ ] Register Test Organization B.
- [ ] Create Agent A in Org A; verify Agent A is invisible to Org B.
- [ ] Issue runtime authorization request; verify gate token single-use execution.
- [ ] Verify webhook dead-letter delivery and audit trail recording.
