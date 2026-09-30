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

# Core Cryptographic Secret (Minimum 64-char hex key, random)
SECRET_KEY=e4a8b79c6aea1c744068f7046870088e24672b497c01146f1f3f8ef01ba603cf

# Authoritative PostgreSQL Database URL (Strictly required in production)
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/[DATABASE]

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
