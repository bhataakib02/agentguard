# AGENTGUARD Staging Environment Variables Inventory & Provisioning Guide

**Document ID**: `AG-ENV-STAGING-01`  
**Classification**: `Restricted / Security & Deployment Baseline`  
**Release Target**: `AGENTGUARD Isolated Staging Environment`  
**Target Infrastructure**: `Render (Web Backend, Worker, Beat, Redis) + Vercel (Frontend) + Supabase (PostgreSQL)`  
**Companion Documents**:
- `docs/deployment/AGENTGUARD_STAGING_INFRASTRUCTURE_PLAN.md`
- `docs/security/AGENTGUARD_STAGING_RLS_MIGRATION_RUNBOOK.md`
- `docs/security/AGENTGUARD_GLOBAL_RATE_LIMITING_IMPLEMENTATION_SPEC.md`

---

## 1. Executive Summary & Strict Change Control Rules

This document defines the complete environment variable inventory, classification taxonomy, safe staging reference values, and cryptographic secret-generation procedures required to provision an isolated AGENTGUARD staging environment.

### 1.1 Non-Negotiable Isolation Rules

1. **Zero Secret Sharing**: Under no circumstances may any production secret, JWT signing key, database credential, Supabase service-role key, encryption key, or third-party API key be reused in the staging environment.
2. **Dedicated Cloud Database**: `DATABASE_URL` in staging must connect exclusively to the dedicated staging PostgreSQL instance (e.g., Supabase project `agentguard-staging`). Connecting staging to the production Supabase project (`xjragvyzlailmtfwjfnm`) is strictly prohibited.
3. **Dedicated Cache & Message Broker**: `REDIS_URL` in staging must connect to a dedicated staging Redis instance (e.g., Render Redis `agentguard-staging-redis`).
4. **Email Containment**: Real production user emails must never be sent from staging. `EMAIL_PROVIDER` must be set to `MOCK`, `NONE`, or a sandboxed staging inbox provider with controlled destination routing.
5. **No Production Plaintext Logging**: Secrets must be injected exclusively via Render and Vercel encrypted environment dashboards. Never commit `.env` files into Git.

---

## 2. Cryptographic Secret Generation Procedures

All staging secrets must be generated using cryptographically secure pseudo-random number generators (CSPRNG) prior to injection into the Render and Vercel staging dashboards.

### 2.1 Backend Cryptographic Master Keys

Execute the following commands in an isolated operator shell (PowerShell or Bash) to generate distinct staging secrets:

```bash
# 1. Generate Application Session & JWT Secret Key (64 hex characters = 256 bits)
openssl rand -hex 32
# Output format: a1b2c3d4e5f6... (use for SECRET_KEY)

# 2. Generate Local AES-256 GCM Master Key for Tenant Integration Secret Encryption (64 hex chars = 32 raw bytes)
openssl rand -hex 32
# Output format: 7f8e9d0c1b2a... (use for LOCAL_AES_MASTER_KEY)

# 3. Generate Ed25519 Private Key for AgentGuard Passport Signature (PEM PKCS8 format)
openssl genpkey -algorithm ed25519 -out staging_passport_ed25519.pem
# Convert to base64 single-line string for environment variable injection:
base64 -w 0 staging_passport_ed25519.pem
# (use for AGENTGUARD_PASSPORT_PRIVATE_KEY)

# 4. Generate Internal Staging Webhook Verification Secret
openssl rand -hex 32
```

---

## 3. Environment Variable Classification Matrix

Each environment variable is classified across three operational axes:

| Axis | Possible Classifications | Definition |
| :--- | :--- | :--- |
| **Requirement Level** | `Required` / `Optional` | `Required` halts service startup if missing; `Optional` activates optional features or uses safe defaults. |
| **Sensitivity** | `Secret` / `Non-Secret` | `Secret` requires encrypted secrets storage; `Non-Secret` can be displayed in build logs and plaintext templates. |
| **Scope / Target** | `Staging-Only` / `Production-Only` / `Common (Different Value)` | `Staging-Only` applies solely to staging; `Common` is required in both but **must have distinct values**. |

---

## 4. Backend Environment Variable Inventory

### 4.1 Core Application & Cryptography

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | **Required** | Non-Secret | Common | `staging` | Set explicitly to `staging`. Never set to `production` in staging. |
| `SECRET_KEY` | **Required** | **Secret** | Common (Distinct) | *`[GENERATE-NEW-64-HEX]`* | Must be newly generated via `openssl rand -hex 32`. Rejection on len < 32. |
| `LOCAL_AES_MASTER_KEY` | **Required** | **Secret** | Common (Distinct) | *`[GENERATE-NEW-64-HEX]`* | Must be newly generated via `openssl rand -hex 32`. Used for vault encryption. |
| `LOCAL_AES_MASTER_KEY_PREVIOUS` | Optional | **Secret** | Common (Distinct) | *(empty on initial staging)* | Used only during key rotation drills. Leave blank for fresh staging. |
| `ALLOW_LOCAL_LOGIN` | **Required** | Non-Secret | Staging-Only | `True` | Permits staging test accounts to authenticate via email/password during testing. |
| `DEFAULT_USER_PASSWORD` | Optional | Non-Secret | Staging-Only | `StagingGuardTest2026!` | Used solely for ephemeral automated test seeding if authorized. |
| `AUTO_BOOTSTRAP_DB` | **Required** | Non-Secret | Staging-Only | `False` | Prevents uncoordinated DDL migration during web server boot. Schema managed via runbook. |
| `RENDER_GIT_COMMIT` | Optional | Non-Secret | Common | *(Injected by Render)* | Render automatically populates the deployment Git commit hash. |

### 4.2 Network, CORS & Host Protection

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `CORS_ORIGINS` | **Required** | Non-Secret | Staging-Only | `https://staging.agentguard.io,https://agentguard-staging.vercel.app` | Comma-separated list of staging web origins. Do not include production domain. |
| `CORS_ORIGIN_REGEX` | Optional | Non-Secret | Staging-Only | `^https://([a-zA-Z0-9_-]+\.)?vercel\.app$` | Allows Vercel staging preview branches while testing. |
| `TRUSTED_HOSTS` | **Required** | Non-Secret | Staging-Only | `agentguard-staging-backend.onrender.com,localhost,127.0.0.1` | Host header validation list. Must include staging Render backend hostname. |

### 4.3 Database & Supabase Configuration

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Required** | **Secret** | Common (Distinct) | `postgresql://postgres:[STAGING-PW]@db.[STAGING-REF].supabase.co:5432/postgres` | Connects to the **dedicated staging Supabase database**. Never use production DB. |
| `DB_POOL_SIZE` | Optional | Non-Secret | Common | `10` | SQLAlchemy pool size for staging traffic. |
| `DB_MAX_OVERFLOW` | Optional | Non-Secret | Common | `20` | Max overflow connections above pool size. |
| `DB_POOL_TIMEOUT` | Optional | Non-Secret | Common | `30` | Seconds to wait before timing out connection acquisition. |
| `SUPABASE_URL` | **Required** | Non-Secret | Common (Distinct) | `https://[STAGING-PROJECT-ID].supabase.co` | Dedicated Staging Supabase project URL. |
| `SUPABASE_PUBLISHABLE_KEY` | **Required** | Non-Secret | Common (Distinct) | `sb_publishable_[STAGING-KEY]` | Public staging Supabase API key. |
| `SUPABASE_JWT_SECRET` | **Required** | **Secret** | Common (Distinct) | *`[STAGING-SUPABASE-JWT-SECRET]`* | Extracted from Staging Supabase Dashboard -> Project Settings -> API. |
| `SUPABASE_SERVICE_ROLE_KEY` | **Required** | **Secret** | Common (Distinct) | *`[STAGING-SERVICE-ROLE-KEY]`* | High-privilege key for admin backend operations in staging. |

### 4.4 Redis, Caching & Distributed Workers (Celery)

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `REDIS_URL` | **Required** | **Secret** | Common (Distinct) | `rediss://default:[STAGING-REDIS-PW]@agentguard-staging-redis:6379` | Dedicated Staging Redis instance on Render or Upstash. |
| `CELERY_BROKER_URL` | **Required** | **Secret** | Common (Distinct) | `rediss://default:[STAGING-REDIS-PW]@agentguard-staging-redis:6379/0` | Points to staging Redis database 0. |
| `CELERY_RESULT_BACKEND` | **Required** | **Secret** | Common (Distinct) | `rediss://default:[STAGING-REDIS-PW]@agentguard-staging-redis:6379/0` | Points to staging Redis database 0. |
| `CELERY_TASK_ALWAYS_EAGER` | **Required** | Non-Secret | Staging-Only | `False` | Must be `False` in staging to verify true async background worker execution. |

### 4.4.1 Global Distributed Rate Limiting (AG-SEC-02)

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RATE_LIMIT_ENABLED` | **Required** | Non-Secret | Common | `True` | Global rate limiting toggle. Must remain enabled in staging and production. |
| `RATE_LIMIT_REDIS_URL` | Optional | **Secret** | Common (Distinct) | `rediss://default:[STAGING-REDIS-PW]@agentguard-staging-redis:6379` | Dedicated Redis URL for rate limiting; falls back to `REDIS_URL` if empty. |
| `RATE_LIMIT_PUBLIC_LIMIT` | Optional | Non-Secret | Common | `60` | Public / general API rate limit in requests per 60-second window. |
| `RATE_LIMIT_AUTH_LIMIT` | Optional | Non-Secret | Common | `5` | Sensitive authentication limit (login, register, OTP) per 60-second window. |
| `RATE_LIMIT_MACHINE_AUTH_LIMIT` | Optional | Non-Secret | Common | `30` | Machine Agent Auth (`/runtime/auth`) limit per 60-second window (fail-closed). |
| `RATE_LIMIT_API_KEY_LIMIT` | Optional | Non-Secret | Common | `1200` | API key / machine token limit per organization per 60-second window. |
| `RATE_LIMIT_AI_USER_LIMIT` | Optional | Non-Secret | Common | `20` | AI assistant / LLM inference limit per authenticated user per 60-second window. |
| `RATE_LIMIT_AI_TENANT_LIMIT` | Optional | Non-Secret | Common | `100` | AI assistant aggregate limit per tenant per 60-second window. |
| `RATE_LIMIT_WINDOW_SECONDS` | Optional | Non-Secret | Common | `60` | Rolling sliding-window duration in seconds. |
| `RATE_LIMIT_STORAGE_BACKEND` | Optional | Non-Secret | Staging-Only | `AUTO` | `AUTO` (uses Redis if available, memory fallback in dev), `REDIS`, or `MEMORY`. |
| `RATE_LIMIT_TRUSTED_PROXIES` | Optional | Non-Secret | Common | `127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` | Comma-separated trusted reverse proxy CIDR networks for anti-spoofing. |
| `RATE_LIMIT_TRUST_CLOUDFLARE_HEADERS` | Optional | Non-Secret | Staging-Only | `False` | Only enable (`True`) if edge proxy is verified Cloudflare terminating at staging. |

### 4.5 Email & Notification Delivery

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `EMAIL_PROVIDER` | **Required** | Non-Secret | Staging-Only | `MOCK` *(or `SMTP` with Mailtrap)* | Set to `MOCK` or `SMTP`. Prevents accidental email dispatch to real users. |
| `BREVO_API_KEY` | Optional | **Secret** | Common (Distinct) | *(leave blank in staging if using MOCK)* | If testing Brevo sandbox, use staging sub-account key. |
| `BREVO_FROM_EMAIL` | Optional | Non-Secret | Common | `staging-noreply@agentguard.io` | Verified staging sender identity. |
| `BREVO_FROM_NAME` | Optional | Non-Secret | Common | `AGENTGUARD Staging` | Clear sender label identifying staging traffic. |
| `RESEND_API_KEY` | Optional | **Secret** | Common (Distinct) | *(leave blank in staging)* | Never use production Resend API key. |
| `SMTP_HOST` | Optional | Non-Secret | Staging-Only | `sandbox.smtp.mailtrap.io` | Staging virtual mailbox / capture sandbox host. |
| `SMTP_PORT` | Optional | Non-Secret | Staging-Only | `587` | Mailtrap sandbox port. |
| `SMTP_USERNAME` | Optional | **Secret** | Staging-Only | *`[MAILTRAP-STAGING-USER]`* | Staging sandbox credential. |
| `SMTP_PASSWORD` | Optional | **Secret** | Staging-Only | *`[MAILTRAP-STAGING-PASS]`* | Staging sandbox credential. |
| `SMTP_USE_TLS` | Optional | Non-Secret | Staging-Only | `True` | Enforces TLS connection to sandbox. |
| `SMTP_FROM_EMAIL` | Optional | Non-Secret | Staging-Only | `staging-alerts@agentguard.io` | Header from-address. |

### 4.6 AI Providers & Intelligence (Sandboxed Mocking vs Dedicated Keys)

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `LLM_PROVIDER` | Optional | Non-Secret | Common | `AUTO` *(or `NONE` for unit tests)* | Determines AI assistant fallback provider. |
| `OPENAI_API_KEY` | Optional | **Secret** | Common (Distinct) | `sk-proj-staging-...` *(spend-capped)* | Dedicated staging OpenAI key with a strictly enforced \$20/month quota limit. |
| `OPENAI_MODEL` | Optional | Non-Secret | Common | `gpt-4o-mini` | Cost-effective model for staging verification. |
| `ANTHROPIC_API_KEY` | Optional | **Secret** | Common (Distinct) | `sk-ant-staging-...` *(spend-capped)* | Dedicated staging key with hard spending limits. |
| `ANTHROPIC_MODEL` | Optional | Non-Secret | Common | `claude-3-5-sonnet-20241022` | Staging evaluation model. |
| `GEMINI_API_KEY` | Optional | **Secret** | Common (Distinct) | `AIzaSy-staging-...` | Dedicated staging Google AI Studio key. |
| `GEMINI_MODEL` | Optional | Non-Secret | Common | `gemini-1.5-flash` | Fast staging validation model. |

### 4.7 Object Storage, SIEM & Sandboxing

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `OBJECT_STORAGE_PROVIDER` | Optional | Non-Secret | Staging-Only | `LOCAL` *(or `S3` with staging bucket)* | Keep `LOCAL` for containerized runs or use isolated staging S3 bucket. |
| `S3_ENDPOINT` | Optional | Non-Secret | Common | *(blank or staging endpoint)* | Custom S3 / MinIO endpoint if configured. |
| `S3_BUCKET` | Optional | Non-Secret | Common (Distinct) | `agentguard-staging-reports` | Dedicated staging bucket. Never use production bucket. |
| `S3_ACCESS_KEY` | Optional | **Secret** | Common (Distinct) | *`[STAGING-S3-KEY]`* | Scoped IAM user for staging bucket only. |
| `S3_SECRET_KEY` | Optional | **Secret** | Common (Distinct) | *`[STAGING-S3-SECRET]`* | Scoped IAM secret. |
| `S3_REGION` | Optional | Non-Secret | Common | `us-east-1` | S3 region. |
| `SIEM_FORWARDER_URL` | Optional | Non-Secret | Common (Distinct) | `https://staging-siem.agentguard.io/v1/logs` | Staging log collector URL. |
| `SIEM_AUTH_TOKEN` | Optional | **Secret** | Common (Distinct) | *`[STAGING-SIEM-TOKEN]`* | Dedicated token for staging log pipeline. |
| `SIEM_PROVIDER` | Optional | Non-Secret | Common | `GENERIC_HTTP` | SIEM transport protocol. |
| `SANDBOX_PROVIDER` | Optional | Non-Secret | Staging-Only | `MOCK_TEST_WORKER` | Safe mock provider for staging environment. |
| `SANDBOX_ALLOW_NETWORK` | Optional | Non-Secret | Staging-Only | `False` | Prevents outbound network calls from sandbox workers. |

### 4.8 Billing, Webhooks & Integrations

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Secret Generation / Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `STRIPE_SECRET_KEY` | Optional | **Secret** | Common (Distinct) | `sk_test_...` | Must be a Stripe **Test Mode** secret key. |
| `STRIPE_PUBLISHABLE_KEY` | Optional | Non-Secret | Common (Distinct) | `pk_test_...` | Stripe **Test Mode** publishable key. |
| `STRIPE_WEBHOOK_SECRET` | Optional | **Secret** | Common (Distinct) | `whsec_staging_...` | Generated in Stripe Dashboard for staging endpoint webhook. |
| `BILLING_WEBHOOK_VERIFICATION_MANDATORY` | **Required** | Non-Secret | Common | `True` | Enforces cryptographic signature verification on billing webhooks. |
| `RAZORPAY_KEY_ID` | Optional | Non-Secret | Common (Distinct) | `rzp_test_...` | Razorpay **Test Mode** key ID. |
| `RAZORPAY_KEY_SECRET` | Optional | **Secret** | Common (Distinct) | *`[RAZORPAY-TEST-SECRET]`* | Razorpay **Test Mode** secret. |
| `AGENTGUARD_ALLOW_LOCAL_TOOLS` | **Required** | Non-Secret | Staging-Only | `False` | Prevents agents from executing SSRF/local tool calls in staging. |
| `AGENTGUARD_ALLOW_LOCAL_SANDBOX` | **Required** | Non-Secret | Staging-Only | `False` | Prevents local sandbox execution. |

---

## 5. Frontend Environment Variable Inventory (Vercel Staging)

Frontend variables are injected during Vercel build time and runtime for the staging environment.

| Variable Name | Requirement | Sensitivity | Scope | Safe Staging Placeholder / Default | Sourcing Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_SITE_URL` | **Required** | Non-Secret | Staging-Only | `https://agentguard-staging.vercel.app` | Staging frontend deployment canonical URL. |
| `NEXT_PUBLIC_API_URL` | **Required** | Non-Secret | Staging-Only | `https://agentguard-staging-backend.onrender.com/api` | Points directly to the **Staging Backend API**. |
| `NEXT_PUBLIC_WS_URL` | **Required** | Non-Secret | Staging-Only | `wss://agentguard-staging-backend.onrender.com/ws` | Staging WebSocket live telemetry endpoint. |
| `NEXT_PUBLIC_SUPABASE_URL` | **Required** | Non-Secret | Common (Distinct) | `https://[STAGING-PROJECT-ID].supabase.co` | Dedicated Staging Supabase project URL. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Required** | Non-Secret | Common (Distinct) | `sb_publishable_[STAGING-KEY]` | Public staging Supabase API key for auth clients. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`| **Required** | Non-Secret | Common (Distinct) | `sb_publishable_[STAGING-KEY]` | Alternative alias for Supabase anon key. |
| `BACKEND_API_URL` | Optional | Non-Secret | Staging-Only | `https://agentguard-staging-backend.onrender.com` | Server-side proxy destination used by `next.config.mjs`. |

---

## 6. Staging Overrides vs Production Reference Comparison

| Key Setting | Production Baseline | Staging Target | Security / Isolation Reason |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | `staging` | Prevents production-specific locks while enforcing staging security controls. |
| `ALLOW_LOCAL_LOGIN` | `False` | `True` | Allows QA and security regression tests with seeded credentials. |
| `AUTO_BOOTSTRAP_DB` | `False` | `False` | Ensures schema is modified only via manual migration scripts. |
| `EMAIL_PROVIDER` | `BREVO` (Live) | `MOCK` / `SMTP` (Mailtrap) | Eliminates all possibility of sending emails to real customer addresses. |
| `DATABASE_URL` | `...xjragvyzlailmtfwjfnm...` | `...[staging-project-ref]...` | Complete data layer separation. Zero cross-contamination. |
| `REDIS_URL` | `agentguard-redis` | `agentguard-staging-redis` | Complete worker job and rate-limit cache isolation. |
| `CELERY_TASK_ALWAYS_EAGER` | `False` | `False` | Validates true distributed task queuing under real Redis conditions. |
| `STRIPE_SECRET_KEY` | `sk_live_...` | `sk_test_...` | No actual financial charges can occur in staging. |
| `SANDBOX_PROVIDER` | `NOT_CONFIGURED` | `MOCK_TEST_WORKER` | Controlled execution harness for security tool testing. |

---

## 7. Pre-Deployment Secret Validation Checklist

Before initiating the staging service deployment on Render and Vercel, the release engineer must verify:

- [ ] `SECRET_KEY` was generated with at least 32 bytes (64 hex characters) of CSPRNG entropy.
- [ ] `LOCAL_AES_MASTER_KEY` is completely distinct from the production master key.
- [ ] `DATABASE_URL` contains the host of the dedicated staging Supabase project, verified via hostname inspection.
- [ ] `REDIS_URL` points to the dedicated staging Redis service.
- [ ] `EMAIL_PROVIDER` is verified as `MOCK` or `SMTP` (configured to Mailtrap).
- [ ] `STRIPE_SECRET_KEY` begins with `sk_test_` and never `sk_live_`.
- [ ] No production credentials exist anywhere within `.env` files or deployment scripts.
- [ ] Frontend `NEXT_PUBLIC_API_URL` points to `agentguard-staging-backend.onrender.com` and not the production backend.
