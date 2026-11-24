# AGENTGUARD — PRODUCTION DEPLOYMENT RUNBOOK
**Document Version:** 1.0.0 (Phase 6F Production Hardening)  
**Classification:** Enterprise Control Plane Operations  

---

## 1. System Overview & Deployment Topology

AGENTGUARD operates as a distributed runtime governance plane consisting of:
1. **Frontend Service**: Next.js 14 Web Application (Edge middleware, React 18, TailwindCSS).
2. **Core API Service**: FastAPI 0.100+ ASGI Application (Python 3.10, Uvicorn, SQLAlchemy).
3. **Database Service**: PostgreSQL 15+ (Supabase Managed or AWS RDS/Aurora) with ACID transactions and foreign-key constraints.
4. **Message Broker / Cache**: Redis 7+ for Celery task queuing and multi-node WebSocket Pub/Sub.
5. **Worker Service**: Celery 5.3+ asynchronous workers executing background webhook deliveries, reports, and alerts.
6. **Scheduler Service**: Celery Beat executing periodic scheduled reports, approval SLA escalation, and retry sweeps.

```text
                                [ CLIENT / BROWSER ]
                                         │
                                         ▼ (HTTPS / WSS)
                              [ REVERSE PROXY / NGINX ]
                                ┌────────┴────────┐
                                │                 │
                       (Port 3000)               (Port 8000)
                                ▼                 ▼
                         [ NEXT.JS ]        [ FASTAPI API ]
                                                  │
                            ┌─────────────────────┼─────────────────────┐
                            ▼                     ▼                     ▼
                     [ POSTGRESQL ]        [ REDIS BROKER ]       [ REPORT STORAGE ]
                     (Authoritative)      (Queues & Pub/Sub)     (Local / AWS S3)
                                                  │
                                         ┌────────┴────────┐
                                         ▼                 ▼
                                  [ CELERY WORKER ]  [ CELERY BEAT ]
```

---

## 2. Component Configuration Status

| Component | Status | Operational Classification |
| :--- | :--- | :--- |
| **FastAPI Backend Core** | `CONFIGURED` | **REQUIRED FOR PRODUCTION** |
| **Next.js Frontend UI** | `CONFIGURED` | **REQUIRED FOR PRODUCTION** |
| **PostgreSQL Database** | `CONFIGURED` | **REQUIRED FOR PRODUCTION** |
| **Redis Broker / PubSub** | `CONFIGURED` | **REQUIRED FOR PRODUCTION** (Defaults to eager in local offline tests) |
| **Celery Worker Engine** | `CONFIGURED` | **REQUIRED FOR PRODUCTION** |
| **Celery Beat Scheduler**| `CONFIGURED` | **REQUIRED FOR PRODUCTION** |
| **Report Storage (Local)** | `CONFIGURED` | **DEFAULT STORAGE BACKEND** |
| **Report Storage (S3/GCS)**| `NOT_CONFIGURED` | **OPTIONAL (Enterprise Cloud Archival)** |
| **SMTP Outbound Email** | `NOT_CONFIGURED` | **OPTIONAL (User Invites & Email Alerts)** |
| **Stripe / Razorpay Billing** | `NOT_IMPLEMENTED` | **FUTURE ENTERPRISE EXTENSION** |

---

## 3. Environment Variables & Secret Configuration

### A. Backend Variables (`backend/.env`)

```ini
# Environment Mode
ENVIRONMENT=production

# Core Cryptographic Secret (Minimum 64-char hex key, random; NEVER commit real secrets)
SECRET_KEY=[GENERATE-STRONG-64-CHAR-HEX-OR-BASE64-SECRET]

# Authoritative PostgreSQL Database URL (Strictly required in production)
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/[DATABASE]

# Database DDL Bootstrap: MUST remain false in production to prevent unexpected DDL changes during service startup
AUTO_BOOTSTRAP_DB=false

# Connection Pooling Tuning
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Supabase Auth Integration
SUPABASE_URL=https://[PROJECT-ID].supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_[KEY]
SUPABASE_JWT_SECRET=[SUPABASE-JWT-SECRET]
SUPABASE_SERVICE_ROLE_KEY=[SUPABASE-SERVICE-ROLE-KEY]

# Redis & Celery Message Broker
REDIS_URL=redis://[REDIS-HOST]:6379/0
CELERY_BROKER_URL=redis://[REDIS-HOST]:6379/0
CELERY_RESULT_BACKEND=redis://[REDIS-HOST]:6379/0
CELERY_TASK_ALWAYS_EAGER=false

# CORS & Host Boundaries
CORS_ORIGINS=https://app.agentguard.com,https://agentguard.vercel.app
TRUSTED_HOSTS=api.agentguard.com,localhost,127.0.0.1

# Automated Plan Bootstrap (Set false if managed by external CI migration)
AUTO_BOOTSTRAP_DB=true

# Optional: Outbound Email / SMTP (Status: NOT_CONFIGURED by default)
EMAIL_PROVIDER=SMTP
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=[SENDGRID-API-KEY]
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=governance@agentguard.com

# Optional: Object Storage (Status: NOT_CONFIGURED by default)
OBJECT_STORAGE_PROVIDER=S3
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=agentguard-production-reports
S3_ACCESS_KEY=[AWS-ACCESS-KEY]
S3_SECRET_KEY=[AWS-SECRET-KEY]
S3_REGION=us-east-1
```

### B. Frontend Variables (`frontend/.env.local` or Vercel Environment)

```ini
# Backend API Base URL
NEXT_PUBLIC_API_URL=https://api.agentguard.com/api

# Real-time WebSocket Gateway
NEXT_PUBLIC_WS_URL=wss://api.agentguard.com/ws

# Supabase Auth Client
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT-ID].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_[KEY]
```

> [!CAUTION]
> Never include `SECRET_KEY`, `DATABASE_URL`, or `SUPABASE_SERVICE_ROLE_KEY` inside `NEXT_PUBLIC_*` frontend variables!

---

## 4. Production Deployment Procedures

### Step 1: PostgreSQL Provisioning & Migrations
1. Ensure the PostgreSQL database instance is accessible and healthy.
2. In production, run the canonical migration scripts:
   ```bash
   psql -h <HOST> -U <USER> -d <DATABASE> -f supabase/migrations/20260831000000_agentguard_schema.sql
   psql -h <HOST> -U <USER> -d <DATABASE> -f supabase/migrations/20260929000000_seed_canonical_plans.sql
   ```
3. Alternatively, when `AUTO_BOOTSTRAP_DB=true`, the backend automatically runs `Base.metadata.create_all()` and idempotently seeds the canonical plans (`FREE`, `STARTER`, `PROFESSIONAL`, `ENTERPRISE`).

### Step 2: Containerized Stack Startup via Docker Compose
To deploy the entire validated production stack:
```bash
# 1. Export required environment variables
export DATABASE_URL="postgresql://user:password@pg-host:5432/agentguard"
export SECRET_KEY="$(openssl rand -hex 32)"

# 2. Build and start containers with healthcheck dependencies
docker-compose up -d --build

# 3. Verify container statuses
docker-compose ps
```

The stack enforces dependency startup ordering:
$$\text{Redis (healthy)} \longrightarrow \text{API (healthy)} \longrightarrow \text{Worker \& Beat}$$

### Step 3: Frontend Deployment (Vercel or Container)
```bash
cd frontend
npm install --production=false
npm run lint
npm run build
npm start
```

---

## 5. Health, Readiness & Liveness Checks

AGENTGUARD provides discrete health probes for container orchestrators (Kubernetes, AWS ECS, Docker):

1. **Liveness Probe** (`GET /health/live` or `GET /health/liveness`):
   - **Purpose**: Checks if the ASGI application process is responsive.
   - **Expected Status**: `200 OK`
   - **Response**: `{"status": "ALIVE", "process": "RUNNING", "timestamp": "..."}`

2. **Readiness Probe** (`GET /health/ready` or `GET /health/readiness`):
   - **Purpose**: Verifies that the service can actively reach PostgreSQL to serve requests.
   - **Expected Status**: `200 OK` (or `503 Service Unavailable` if database connectivity fails).
   - **Response**: `{"status": "READY", "database": "CONNECTED", "timestamp": "..."}`

3. **Subsystem Dependency Health** (`GET /api/system/health`):
   - **Purpose**: Authenticated deep inspection of all connected platform dependencies (Database, Redis, Worker, Scheduler, Storage, Email, WebSockets).

---

## 6. Backup & Disaster Recovery Runbook

### A. Automated Backup Creation
Run the backup drill script or invoke `pg_dump`:
```bash
python backend/scripts/backup_restore.py
```
Or directly via PostgreSQL CLI:
```bash
pg_dump -h <HOST> -p 5432 -U <USER> -d agentguard -F c -b -v -f /backups/agentguard_$(date +%Y%m%d_%H%M%S).dump
```

### B. Safe Restore Procedure
```bash
# 1. Verify dump file integrity
pg_restore -l /backups/agentguard_20260930.dump

# 2. Restore into target database
pg_restore -h <HOST> -p 5432 -U <USER> -d agentguard_restored -v --clean --if-exists /backups/agentguard_20260930.dump

# 3. Execute integrity verification script
python backend/scripts/backup_restore.py
```

---

## 7. Operational Troubleshooting & Failure Recovery

### Incident A: Redis Broker Unavailable
- **Impact**: Celery task queueing degrades; background jobs fallback to eager execution or queue backlogs. WebSocket broadcast falls back to `SINGLE_NODE` in-memory routing.
- **Recovery**:
  1. Restart Redis container: `docker-compose restart redis`
  2. Inspect logs: `docker-compose logs --tail=100 redis`
  3. Verify port 6379 connectivity: `redis-cli ping`

### Incident B: Webhook Delivery Retries Exhausted (DLQ)
- **Impact**: Endpoint moves to `DEAD_LETTER` state after 3 failed attempts (with 30s, 120s, 480s backoff).
- **Recovery**:
  1. Inspect failed delivery via API: `GET /api/webhooks/deliveries?status=DEAD_LETTER`
  2. Revalidate target URL for SSRF or network drops.
  3. Re-trigger delivery: `POST /api/webhooks/{webhook_id}/deliveries/{delivery_id}/retry`

### Incident C: Database Connection Saturation
- **Impact**: Requests experience latency or return `503 Service Unavailable` on readiness probe.
- **Recovery**:
  1. Inspect active connections: `SELECT count(*) FROM pg_stat_activity;`
  2. Adjust `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` in `backend/config.py`.
  3. Verify connection pool recycle settings (`pool_recycle=300, pool_pre_ping=True`).

---

## 8. Pre-Flight Security Checklist

- [x] Production environment set: `ENVIRONMENT=production`
- [x] Zero hardcoded secrets in source code or git history
- [x] `.env` files added to `.gitignore`
- [x] Strict CORS configured with explicit allowed origins (no wildcard `*`)
- [x] Safe AST evaluation active (zero `eval()` or `exec()`)
- [x] Tenant isolation validated across all 20+ entities
- [x] SSRF blocking active for all outbound webhook requests
- [x] HMAC-SHA256 signatures generated for all webhook dispatches
- [x] Unconfigured cloud services truthfully declare `NOT_CONFIGURED`

---

## 9. Cryptographic Key Rotation Runbook

### A. Passport Signing Key Rotation (Ed25519)
AGENTGUARD employs asymmetric Ed25519 digital signatures for agent passports. Each passport is stamped with the `key_id` of the platform signing key active at issuance.

1. **Architecture & Multi-Key Keyring**:
   - `PassportSigningService` maintains an in-memory keyring `_trusted_keys = {key_id: public_key}`.
   - When a new key is rotated in via `rotate_active_key(new_key_id, new_private_key)`, the previous active key remains in the trusted keyring.
   - Historical passports signed by older keys continue to verify cleanly until their natural expiration.
   - Any passport presenting an unrecognized or missing `key_id` fails closed (`UNKNOWN_KEY_ID`).

2. **Rotation Procedure**:
   - Generate a new Ed25519 platform private key using a secure offline utility or AWS KMS / Vault.
   - Provision the new key and key identifier to backend configuration.
   - Restart the backend instances; new agent passports will automatically receive signatures using the new key ID while existing passports verify against the trusted historical keys.

### B. Webhook Secret Encryption-At-Rest Rotation (AES-256-GCM)
Outbound webhook secrets are encrypted at rest using AES-256-GCM authenticated encryption prefixed with `enc:aesgcm:<nonce_b64>:<ciphertext_b64>`.

1. **Key Derivation**:
   - Encryption keys are derived via HKDF-SHA256 from `settings.SECRET_KEY`.
   - Tampered ciphertext or corrupted authentication tags fail closed and halt outbound delivery with a security alert.

2. **Legacy Secret Migration**:
   - For environments with existing unencrypted webhook secrets, run the idempotent migration tool:
     ```bash
     python backend/scripts/migrate_webhook_secrets.py --dry-run
     python backend/scripts/migrate_webhook_secrets.py --execute
     ```
   - The script encrypts unencrypted records without logging secret values.

3. **Master Secret Key Rotation Procedure**:
   - In the event of `SECRET_KEY` rotation:
     a. Decrypt existing webhook secrets into transient memory using the current `SECRET_KEY`.
     b. Re-encrypt all secrets with the new `SECRET_KEY`.
     c. Commit re-encrypted records and update environment configuration.

---

## 10. Render Cloud Deployment Runbook (Redis, Celery Worker & Beat)

### A. Render Services Topology
AGENTGUARD's Render Blueprint (`render.yaml`) provisions four tightly integrated services in the Singapore region:

| Service Name | Service Type | Runtime / Plan | Purpose |
| :--- | :--- | :--- | :--- |
| **`agentguard-redis`** | `keyvalue` | `starter` | Managed Redis/Valkey broker for task distribution & Pub/Sub |
| **`agentguard-backend`** | `web` | `python` / `starter` | FastAPI ASGI web application serving HTTP and WebSockets |
| **`agentguard-worker`** | `worker` | `python` / `starter` | Celery asynchronous worker consuming background tasks |
| **`agentguard-beat`** | `worker` | `python` / `starter` | Celery Beat singleton scheduler dispatching periodic tasks |

### B. Startup Commands
Each service executes from the `backend/` working directory (`rootDir: backend`):

1. **Web API (`agentguard-backend`)**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT --ws-ping-interval 20 --ws-ping-timeout 20
   ```
2. **Celery Worker (`agentguard-worker`)**:
   ```bash
   celery -A celery_app.celery_app worker --loglevel=info --concurrency=4 -Q celery
   ```
   - Consumes exclusively from the primary `celery` queue where tasks are routed.
   - Concurrency set to 4 execution threads/processes.
   - Does NOT run an HTTP server or bind to `$PORT`.
3. **Celery Beat (`agentguard-beat`)**:
   ```bash
   celery -A celery_app.celery_app beat --loglevel=info
   ```
   - Configured with `numInstances: 1` to guarantee a single scheduler instance.
   - Dispatches tasks to the Redis broker according to `beat_schedule`.
   - Does NOT consume tasks or run an HTTP server.

### C. Redis Broker Architecture
- **Service**: Render Key Value (`type: keyvalue`, plan `starter`).
- **Access Control**: `ipAllowList: []` isolates Redis strictly to Render's internal private network.
- **Eviction Policy**: `maxmemoryPolicy: noeviction` ensures Celery queues never drop pending tasks under memory pressure.
- **Dynamic Ingestion**: Web, Worker, and Beat dynamically receive the internal connection string via `fromService`:
  ```yaml
  - key: REDIS_URL
    fromService:
      type: keyvalue
      name: agentguard-redis
      property: connectionString
  - key: CELERY_BROKER_URL
    fromService:
      type: keyvalue
      name: agentguard-redis
      property: connectionString
  - key: CELERY_RESULT_BACKEND
    fromService:
      type: keyvalue
      name: agentguard-redis
      property: connectionString
  ```
- **Zero Credentials in Code**: Connection passwords and host addresses are automatically managed by Render.

### D. Required Environment Variables

#### 1. Shared Non-Secret Variables (`envVarGroups: agentguard-shared`)
- `PYTHON_VERSION=3.10.12`
- `ENVIRONMENT=production`
- `PROJECT_NAME=AGENTGUARD`
- `API_V1_STR=/api`
- `AUTO_BOOTSTRAP_DB=false` (Schema migrations managed explicitly; DDL on startup disabled)
- `ALLOW_LOCAL_LOGIN=false` (Strictly enforces Supabase authentication in production)
- `CELERY_TASK_ALWAYS_EAGER=false` (Forces asynchronous dispatch via Redis broker)

#### 2. Service Secrets (`sync: false`)
During Blueprint deployment or in the Render Dashboard, provision the following secrets for `agentguard-backend`, `agentguard-worker`, and `agentguard-beat`:
- `DATABASE_URL`: Production PostgreSQL connection string (`postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/[DATABASE]`).
- `SECRET_KEY`: High-entropy 64-character signing secret (`openssl rand -hex 32`).
- `SUPABASE_URL`: Supabase project URL (`https://[PROJECT-ID].supabase.co`).
- `SUPABASE_PUBLISHABLE_KEY`: Supabase client anon/publishable key.
- `SUPABASE_JWT_SECRET`: Supabase JWT secret for validating access tokens.

### E. Operational Verification Procedures

#### 1. Verifying Worker is Consuming Tasks
Inspect the Render deployment logs for `agentguard-worker`:
```text
[2026-11-24 16:00:00,000: INFO/MainProcess] Connected to redis://red-xxxx:6379//
[2026-11-24 16:00:00,100: INFO/MainProcess] mingle: searching for neighbors
[2026-11-24 16:00:01,200: INFO/MainProcess] mingle: all OK
[2026-11-24 16:00:01,300: INFO/MainProcess] celery@agentguard-worker ready.
[2026-11-24 16:00:01,350: INFO/MainProcess] [queues]
    . celery exchange=celery(direct) key=celery
[2026-11-24 16:00:01,400: INFO/MainProcess] [tasks]
    . tasks.auth_tasks.cleanup_expired_otp_challenges_task
    . tasks.escalation_tasks.escalate_approvals_task
    . tasks.notification_tasks.deliver_notification_task
    . tasks.report_tasks.execute_scheduled_reports_task
    . tasks.retention_tasks.purge_expired_data_task
    . tasks.sandbox_tasks.cleanup_expired_sandbox_artifacts_task
    . tasks.siem_tasks.retry_pending_siem_deliveries_task
    . tasks.webhook_tasks.dispatch_webhook_task
    . tasks.webhook_tasks.retry_pending_webhooks_task
```
Or check worker health via authenticated API:
```bash
GET /api/system/health
```
Expected response:
```json
{
  "worker": {
    "status": "HEALTHY",
    "mode": "DISTRIBUTED",
    "active_workers": 1,
    "worker_nodes": ["celery@agentguard-worker-..."]
  }
}
```

#### 2. Verifying Beat is Dispatching Hourly OTP Cleanup
Inspect the Render deployment logs for `agentguard-beat`:
```text
[2026-11-24 16:00:00,000: INFO/MainProcess] beat: Starting...
[2026-11-24 16:00:00,100: INFO/MainProcess] Writing entries...
[2026-11-24 17:00:00,000: INFO/MainProcess] Scheduler: Sending due task cleanup-expired-otp-challenges (tasks.auth_tasks.cleanup_expired_otp_challenges_task)
```
Simultaneously, `agentguard-worker` logs will record task receipt and execution:
```text
[2026-11-24 17:00:00,050: INFO/MainProcess] Task tasks.auth_tasks.cleanup_expired_otp_challenges_task[...] received
[2026-11-24 17:00:00,200: INFO/ForkPoolWorker-1] [AuthCleanup] Successfully processed 0 expired/abandoned OTP challenges.
[2026-11-24 17:00:00,210: INFO/ForkPoolWorker-1] Task tasks.auth_tasks.cleanup_expired_otp_challenges_task[...] succeeded in 0.015s
```

#### 3. How to Safely Test OTP Cleanup in Staging
To test the OTP cleanup task in a staging environment without waiting for the hourly schedule:
1. Trigger task directly via staging Celery worker CLI or Python shell:
   ```bash
   python -c "
   from celery_app import celery_app
   from tasks.auth_tasks import cleanup_expired_otp_challenges_task
   res = cleanup_expired_otp_challenges_task.apply_async(args=[500, 1])
   print('Task dispatched:', res.id)
   print('Result:', res.get(timeout=10))
   "
   ```
2. Verify the task output:
   ```json
   {
     "status": "COMPLETED",
     "cleaned_count": 0,
     "timestamp": "2026-11-24T17:00:00.000000"
   }
   ```
3. Run the automated staging test runner:
   ```bash
   python backend/scripts/verify_render_deployment.py
   pytest backend/tests/test_otp_cleanup_and_reconciliation.py -v
   ```

#### 4. Diagnosing Redis Connection and Celery Import Failures
- **Symptom: `Broker unreachable` or `redis.exceptions.ConnectionError`**:
  - Check that `agentguard-redis` is healthy and in the same region (`singapore`).
  - Verify `REDIS_URL` is populated in service environment: Render automatically injects `fromService`.
  - Ensure `ipAllowList: []` is present (allowing internal private connections within Render).
  - Test broker reachability via `inspect_broker_health()` in `celery_app.py`.
- **Symptom: `ModuleNotFoundError` or `ImportError: cannot import name celery_app`**:
  - Verify `rootDir: backend` is specified in `render.yaml` for both Worker and Beat.
  - Verify module specifier is `celery_app.celery_app` (module `celery_app`, object `celery_app`).
  - Ensure all dependencies in `requirements.txt` installed cleanly during `buildCommand: pip install -r requirements.txt`.

#### 5. Recovery if Beat Process Stops
Render automatically restarts failed background workers if their process exits.
If Celery Beat fails to recover or becomes stalled:
1. In the Render Dashboard, navigate to `agentguard-beat` -> **Manual Deploy** -> **Restart Service**.
2. If Beat was stopped due to a corrupt schedule database file (`celerybeat-schedule` lock):
   - Trigger a clean deploy: Render containers are ephemeral, so redeploying provisions a fresh container and clears any stale lockfile.
3. Verify only one Beat instance is running (`numInstances: 1`). Never scale Beat horizontally; duplicate Beat instances will dispatch duplicate periodic tasks.

