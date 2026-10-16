# AGENTGUARD Operations & Runbooks

Welcome to the AGENTGUARD Operational Runbooks directory. This folder provides standardized, step-by-step procedures for deploying, configuring, monitoring, and operating the AGENTGUARD control plane in both local development and production cloud environments.

---

## 1. Available Runbooks

- [Production Deployment Runbook](DEPLOYMENT_RUNBOOK.md): Complete guide to production architecture, container topology, environment variables, PostgreSQL/Supabase database setup, Redis broker configuration, Celery worker/beat topology, SSL/TLS, and Render/Vercel platform deployment.
- [Local Development Workflow](DEVELOPMENT_WORKFLOW.md): Day-to-day developer workflow for Windows, macOS, and Linux including virtual environment setup, database bootstrapping, FastAPI backend startup, Next.js frontend serving, and regression testing.

---

## 2. Quick Command Reference

### Local Development

1. **Start Backend Server:**
   ```bash
   cd backend
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start Frontend Dashboard:**
   ```bash
   cd frontend
   npm run dev
   ```

### Docker Compose Multi-Service Stack

```bash
# Start Redis, FastAPI API, Celery Worker, and Celery Beat
docker-compose up --build -d
```
