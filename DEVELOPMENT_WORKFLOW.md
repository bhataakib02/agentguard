# AGENTGUARD Local Development Workflow (Windows)

This document provides a repeatable local development and testing guide for running AGENTGUARD, its Predictive Action Control Engine (PACE), and the Simulation & Evaluation Lab on Windows.

---

## 1. Prerequisites and Environment

### System Prerequisites
- **Operating System:** Windows 10/11 x64 or Windows Server 2022+
- **Python:** Python 3.10.x or 3.11.x (installed and added to `PATH`)
- **Node.js:** Node.js v18.x or v20.x LTS + `npm`
- **Database:** SQLite (default for local development and test suites) or PostgreSQL / Supabase
- **Redis (Optional):** Used for rate limiting in distributed deployments; in-memory fallback is active by default locally.

### Required Environment Variables
Configure these variables in your environment or in `backend/.env`. **Never commit secrets to source control.**

| Variable Name | Description | Default / Local Development Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | Database connection URI | `sqlite:///./agentguard_dev.db` |
| `SECRET_KEY` | HMAC token signing secret | *[Generate strong local random string]* |
| `ENVIRONMENT` | Runtime deployment tier | `development` or `test` |
| `AGENTGUARD_ALLOW_LOCAL_TOOLS` | Permits execution of registered local test tools | `true` |
| `ALLOW_DEMO_SEED` | Permits development fixture seeding | `true` (non-production only) |
| `AUTO_BOOTSTRAP_DB` | Automatically provisions DB tables on boot | `true` |
| `API_V1_STR` | Primary API prefix | `/api` |
| `NEXT_PUBLIC_API_URL` | Frontend API target | `http://localhost:8000/api` |

---

## 2. Backend Setup and Startup

### Step 2.1: Python Virtual Environment
Open PowerShell or Windows Terminal in `D:\AGENTGUARD\backend`:
```powershell
cd D:\AGENTGUARD\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2.2: Database Initialization and Seeding
Initialize schema and canonical SaaS plans:
```powershell
python bootstrap.py
```

To seed development organizations and agents (e.g. ACME FinTech, CyberShield):
```powershell
$env:ALLOW_DEMO_SEED = "true"
python scripts/seed_demo_orgs.py
```

### Step 2.3: Starting the Backend API Server
Launch the FastAPI server using Uvicorn:
```powershell
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base: `http://127.0.0.1:8000/api`
- Interactive Swagger Docs: `http://127.0.0.1:8000/docs`
- Liveness Probe: `http://127.0.0.1:8000/api/health/live`
- Readiness Probe: `http://127.0.0.1:8000/api/health/ready`

---

## 3. Frontend Setup and Startup

Open a separate PowerShell terminal in `D:\AGENTGUARD\frontend`:
```powershell
cd D:\AGENTGUARD\frontend
npm install
npm run dev
```
- Frontend Web App: `http://localhost:3000`

---

## 4. Running Verification Test Suites

Execute the comprehensive 74-test regression suite covering PACE Phase 1–3, the Phase 3 Simulation Lab, and Phase 4 Product Integration:
```powershell
cd D:\AGENTGUARD
pytest backend/tests/test_phase4_product_integration.py backend/tests/test_pace_simulation_lab.py backend/tests/test_predictive_action_control_engine.py backend/tests/test_runtime_authorization_suite.py backend/tests/test_phase2_policy_engine.py -v
```

Run frontend static type checking:
```powershell
cd D:\AGENTGUARD\frontend
npx tsc --noEmit
```

---

## 5. Main Application User Journey Navigation

| Route | View Name | Key Workflow Capabilities |
| :--- | :--- | :--- |
| `/agents` | AI Directory | View registered agents, autonomy levels (`LOW`, `MEDIUM`, `HIGH`, `FULL`), and risk scores. |
| `/permissions` | Permission Matrix | Inspect and manage granular tool permissions and machine credentials per agent. |
| `/decisions` | PACE Control Console & Black Box | Evaluate actions with sequence risk delta ($\Delta$), reachability analysis, and test presets. |
| `/approvals` | Human Approval Queue | Managerial review queue for review-required actions held at execution boundary. |
| `/provenance` | Causal Provenance | Trace causal decision trees from human initiator $\to$ agent action $\to$ policy rule $\to$ outcome. |
| `/simulation` | PACE Simulation Lab | Reproducible benchmark harness comparing Baseline vs. PACE across 10 scenario categories. |
| `/audit` | Immutable Audit Logs | Search chronological tamper-evident audit logs across machine agents and human users. |

---

## 6. Troubleshooting Common Issues

### 1. `Execution gate token missing` or `Passport verification failed`
- **Cause:** In PACE, every agent requires a signed cryptographic `AgentPassport`.
- **Fix:** Ensure agent has a signed passport via `passport_service.sign_passport(agent, passport)` or re-run `scripts/seed_demo_orgs.py`.

### 2. SQLite Database Locking on Windows
- **Cause:** Concurrent test runners accessing SQLite concurrently.
- **Fix:** Test suites automatically use isolated databases (`sqlite:///test_*.db`). For local development, avoid running high-concurrency external scripts while uvicorn reload is active.

### 3. Frontend `401 Unauthorized` on `/api/*`
- **Cause:** JWT token expired or missing Authorization header.
- **Fix:** Navigate to `/login` and sign in with demo credentials (e.g. `admin@acmefintech.com`).

### 4. PowerShell Script Execution Policy
- **Cause:** `Activate.ps1 cannot be loaded because running scripts is disabled on this system.`
- **Fix:** Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell.
