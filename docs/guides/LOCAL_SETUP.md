# Local Setup Guide

This guide walks through setting up **AGENTGUARD — Runtime Control Plane for Autonomous AI** on your local workstation for development, evaluation, and testing.

---

## 1. System Prerequisites

Ensure your system meets the following requirements before starting:

1. **Operating System:** Windows 10/11, macOS 12+, or Ubuntu 20.04+ (or equivalent Linux distribution).
2. **Python:** Python 3.10 or 3.11 with `pip` and `venv` enabled.
3. **Node.js:** Node.js 20.x LTS or higher with `npm`.
4. **Git:** Git 2.30+ installed.
5. **Redis (Optional for local unit tests, recommended for background tasks):** Redis 7.x installed locally or running via Docker.

---

## 2. Installation Steps

### Step 1: Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/bhataakib02/agentguard.git
cd agentguard
```

### Step 2: Set Up Backend Virtual Environment

Initialize a Python virtual environment and install the required dependencies:

```bash
cd backend
python -m venv venv

# Activate the virtual environment:
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Upgrade pip and install dependencies:
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create your local backend and frontend configuration files from the examples:

```bash
# In frontend directory:
cd ../frontend
cp .env.example .env.local

# In backend directory:
cd ../backend
```

For local development without an external database, AGENTGUARD automatically defaults to SQLite (`sqlite:///./agentguard_dev.db`). For PostgreSQL / Supabase, set `DATABASE_URL` in `backend/.env`.

### Step 4: Bootstrap Database Schema

Run the database bootstrap script to provision required canonical tables and subscription plans:

```bash
python bootstrap.py
```

### Step 5: Install Frontend Dependencies

From the `frontend/` directory, install all Node modules:

```bash
cd ../frontend
npm install
```

---

## 3. Launching the Application Services

### Step 1: Start the Backend API Server

In your backend terminal with the virtual environment activated:

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The FastAPI API server will be available at:
- REST API Base: `http://127.0.0.1:8000/api`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health/live`

### Step 2: Start the Frontend Dashboard

In a separate terminal window:

```bash
cd frontend
npm run dev
```

The Next.js management dashboard will be available at:
- Web Application: `http://localhost:3000`

---

## 4. Verifying Your Setup

Confirm that the local installation is working properly:

1. **Verify Backend Health:**
   ```bash
   curl -s http://127.0.0.1:8000/health/live
   # Expected response: {"status":"ALIVE","timestamp":...}
   ```

2. **Verify Frontend Route Generation:**
   Open `http://localhost:3000` in your browser. The AGENTGUARD login and platform navigation should render with the green/off-white design system.

3. **Execute Core Test Verification:**
   Run the quick verification suite:
   ```bash
   cd backend
   python -m pytest tests/test_production_readiness.py -v
   ```
