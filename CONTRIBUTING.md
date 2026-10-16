# Contributing to AGENTGUARD

Thank you for your interest in contributing to **AGENTGUARD — Runtime Control Plane for Autonomous AI**! We welcome contributions from developers, security researchers, AI engineers, and technical writers.

This guide outlines our development workflow, coding conventions, testing requirements, and pull request submission process.

---

## 1. Code of Conduct & Security First

AGENTGUARD is an enterprise security product. Every contributor must observe the following core principles:

1. **Security Invariants First:** Never weaken security checks, bypass PACE evaluation gates, bypass tenant isolation, or disable authorization checks to make tests pass.
2. **Zero Hardcoded Secrets:** Never commit real API keys, tokens, passwords, database credentials, or private keys to git.
3. **Respectful Collaboration:** We are committed to providing a welcoming, professional, and harassment-free environment for all contributors.

---

## 2. Development Setup

### 2.1 Prerequisites

Before setting up your local environment, ensure you have:

1. **Python:** Version 3.10 or 3.11 with `pip` and `venv`.
2. **Node.js:** Version 20.x LTS or higher with `npm`.
3. **Redis:** Version 7.x (local service or via Docker).
4. **PostgreSQL / Supabase:** PostgreSQL 15+ database instance (or local SQLite fallback for isolated unit testing).
5. **Docker & Docker Compose:** Optional, for containerized local development.

### 2.2 Local Workspace Installation

Follow these steps to set up the repository:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/bhataakib02/agentguard.git
   cd agentguard
   ```

2. **Configure Backend:**
   ```bash
   cd backend
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # macOS/Linux:
   source venv/bin/activate

   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure Frontend:**
   ```bash
   cd ../frontend
   npm install
   ```

4. **Initialize Environment Configuration:**
   Copy the provided environment examples:
   ```bash
   # From repository root
   cp frontend/.env.example frontend/.env.local
   # Ensure backend/.env contains required test or development database strings
   ```

---

## 3. Branching & Contribution Workflow

All development follows a standard branch-and-PR model:

1. **Branch Naming:** Create a focused feature or fix branch from `main`:
   - Feature branches: `feat/descriptive-name`
   - Bug fixes: `fix/descriptive-name`
   - Documentation updates: `docs/descriptive-name`
   - Chore / refactoring: `chore/descriptive-name`

2. **Commit Messages:** Follow Conventional Commits:
   - `feat(pace): add new prompt injection heuristic filter`
   - `fix(auth): correct token rotation grace period`
   - `docs(api): document websocket subscription payload schema`
   - `test(iam): add cross-tenant authorization isolation test`

3. **Scope and Modularity:** Keep pull requests focused on a single logical change. Large unrelated changes should be split into smaller, reviewable pull requests.

---

## 4. Testing & Quality Requirements

Every pull request must pass the automated verification suites before review:

### 4.1 Backend Quality & Regression Testing

Run the full 12-suite regression run from `backend/`:

```bash
cd backend
python -m pytest tests/test_simulation_iam_alignment.py tests/test_iam_direct.py tests/test_iam_role_matrix.py tests/test_phase1_auth_hardening.py tests/test_phase5_enterprise_iam.py tests/test_dynamic_dataset_evaluation.py tests/test_evaluation_datasets_persistence.py tests/test_predictive_action_control_engine.py tests/test_production_readiness.py tests/test_secret_rotation_and_session_invalidation.py tests/test_p0_security_remediation.py tests/test_platform_super_admin_license_suite.py
```

All 173 tests must pass with zero failures and zero errors (`exit code 0`).

### 4.2 Frontend Quality & Build Verification

Run TypeScript compilation and the production Next.js build from `frontend/`:

```bash
cd frontend
npx tsc --noEmit
npm run lint
npm run build
```

The production build must complete with `exit code 0` and all static/SSG routes successfully generated.

### 4.3 SDK Verification

If your change touches SDK code under `sdks/`:

1. **TypeScript SDK:**
   ```bash
   cd sdks/typescript
   npm run build
   node tests/test_sdk.mjs
   ```
2. **Python SDK:**
   ```bash
   pip install -e sdks/python
   python -m pytest backend/tests/test_sdk_suite.py
   ```

### 4.4 Git Cleanliness

Verify that no whitespace errors, trailing carriage returns, or format errors exist:

```bash
git diff --check
```

---

## 5. Documentation Standards

When contributing documentation or modifying `.md` files:

1. **Sequential Numbering from 1:** Every numbered procedure or sequential list must start at `1` and progress consecutively (`1`, `2`, `3`). Independent lists must restart at `1`.
2. **Relative Markdown Links:** Use repository-relative links (`docs/guides/LOCAL_SETUP.md`) rather than absolute or machine-specific paths (`file:///` or Windows drive paths).
3. **Heading Hierarchy:** Use a single top-level `#` title per document, followed logically by `##` for sections and `###` for subsections. Do not skip heading levels.
4. **Technical Accuracy:** Document actual, verified features. Clearly differentiate between production-ready capabilities and simulated benchmark scenarios.

---

## 6. Pull Request Submission

When your branch is ready:

1. Push your branch to GitHub.
2. Open a Pull Request targeting `main`.
3. Provide a clear description including:
   - Summary of the problem solved or feature added.
   - List of modified components and files.
   - Verification command outputs (test run status, build output).
   - Any architectural or security considerations.
4. Respond promptly to code review feedback. Once approved and all automated checks pass, your change will be merged.

Thank you for contributing to AGENTGUARD!
