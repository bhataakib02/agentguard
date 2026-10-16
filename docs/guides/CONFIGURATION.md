# Configuration & Environment Reference

This guide details all configuration variables, environment settings, and operational flags required to configure **AGENTGUARD** across development, staging, and production environments.

---

## 1. Configuration Principles

AGENTGUARD enforces strict security and environment hygiene standards:

1. **Explicit Secrets via Environment:** Passwords, private keys, HMAC signing secrets, and database credentials must only be injected via environment variables or secret managers (e.g., AWS Secrets Manager, Vault, Render Environment Secrets).
2. **Never Commit Secrets:** `.env` files containing live credentials are explicitly excluded by `.gitignore` and `.dockerignore`.
3. **Fail-Safe Defaults:** In the absence of external Redis or cloud storage, the system gracefully falls back to local in-memory structures or SQLite for non-destructive local developer workflows.

---

## 2. Backend Environment Variables (`backend/.env`)

| Variable | Type | Required in Production | Description & Production Guidance |
| :--- | :---: | :---: | :--- |
| `DATABASE_URL` | String | **Yes** | SQLAlchemy connection URI (e.g., `postgresql://postgres:[PASSWORD]@db.example.supabase.co:5432/postgres`). Defaults to SQLite in local tests. |
| `SECRET_KEY` | String | **Yes** | High-entropy random key used for cryptographic HMAC token signing. Must be generated using `openssl rand -hex 32`. |
| `ENVIRONMENT` | String | **Yes** | Deployment tier: `development`, `staging`, `production`, or `test`. Production activates strict seed script guards. |
| `REDIS_URL` | String | **Yes** | Redis connection URI (e.g., `redis://localhost:6379/0`). Used for Celery message broker and multi-node WebSocket Pub/Sub. |
| `CELERY_BROKER_URL` | String | Optional | Explicit broker URL if distinct from `REDIS_URL`. Defaults to `REDIS_URL`. |
| `CELERY_RESULT_BACKEND` | String | Optional | Result backend URI for asynchronous task outcomes. Defaults to `REDIS_URL`. |
| `PORT` | Integer | Optional | Port for the Uvicorn ASGI server. Defaults to `8000` (auto-bound by Render/Heroku). |
| `API_V1_STR` | String | No | URL prefix for REST API endpoints. Default: `/api`. |
| `PROJECT_NAME` | String | No | Human-readable system name. Default: `AGENTGUARD`. |
| `ALLOWED_ORIGINS` | String | **Yes** | Comma-separated CORS allowed origin list (e.g., `https://dashboard.agentguard.dev`). Default in dev: `*`. |
| `SUPABASE_URL` | String | Optional | Supabase Project REST/Auth endpoint (e.g., `https://[PROJECT].supabase.co`). |
| `SUPABASE_SERVICE_ROLE_KEY` | String | Optional | Elevated backend service-role key for administrative auth operations. |
| `AGENTGUARD_ALLOW_LOCAL_TOOLS`| Boolean | No | Permits execution of mock/local system tools in sandbox evaluation. Default: `false`. |
| `ALLOW_DEMO_SEED` | Boolean | No | Permits execution of manual developer seed scripts. Strictly blocked when `ENVIRONMENT=production`. |

---

## 3. Frontend Environment Variables (`frontend/.env.local`)

All frontend variables intended for client-side consumption must be prefixed with `NEXT_PUBLIC_`:

| Variable | Type | Required | Description |
| :--- | :---: | :---: | :--- |
| `NEXT_PUBLIC_API_URL` | String | **Yes** | Target backend REST API URL. Example: `http://localhost:8000/api` (dev) or `https://api.agentguard.dev/api` (prod). |
| `NEXT_PUBLIC_WS_URL` | String | **Yes** | Target backend WebSocket URL for real-time telemetry and alerts. Example: `ws://localhost:8000/ws` (dev) or `wss://api.agentguard.dev/ws` (prod). |
| `NEXT_PUBLIC_SUPABASE_URL` | String | Optional | Public Supabase project URL for browser-side authentication flows. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | String | Optional | Public anonymous key for browser-side Supabase client initialization. |

> [!CAUTION]
> Never expose `SUPABASE_SERVICE_ROLE_KEY`, `SECRET_KEY`, or database credentials under any `NEXT_PUBLIC_*` variable. Frontend variables are bundled into client-side JavaScript assets.

---

## 4. Docker Compose Environment Configuration

When deploying the full stack via `docker-compose.yml`, configure your environment via `.env` at the repository root:

```bash
# Production Database Connection
DATABASE_URL=postgresql://user:secure_password@postgres:5432/agentguard

# Core Application Cryptographic Secret
SECRET_KEY=e2e307f0c1a938... # Generate with: openssl rand -hex 32

# Deployment Tier
ENVIRONMENT=production
```
