# Testing & Verification Guide

This guide describes how to execute automated testing, regression suites, SDK verification, and frontend builds across the **AGENTGUARD** codebase.

---

## 1. Testing Philosophy & Invariants

All AGENTGUARD testing adheres to five mandatory principles:

1. **Non-Destructive Testing:** Test fixtures execute against isolated test databases or mock scopes. Real production data, organizations, or evaluation datasets are never modified or truncated during test runs.
2. **Deterministic Security Assertion:** Authorization tests verify both positive cases (valid roles succeed) and negative cases (unauthorized roles, missing headers, forged roles receive `401` or `403`).
3. **Zero Test Weakening:** Test assertions must never be commented out or weakened to manufacture passing results.
4. **Complete Coverage:** Regressions must validate backend logic, frontend route generation, and SDK client behavior before merging or deploying.
5. **Clean Formatting:** Every change must satisfy `git diff --check` with zero whitespace errors.

---

## 2. Backend Regression Suite

The backend test suite is executed using `pytest` from the `backend/` directory.

### 2.1 Full Authoritative Regression Run (173 Tests)

Execute the complete 12-suite regression run covering IAM, PACE, authentication, evaluation datasets, and platform security:

```bash
cd backend
python -m pytest tests/test_simulation_iam_alignment.py tests/test_iam_direct.py tests/test_iam_role_matrix.py tests/test_phase1_auth_hardening.py tests/test_phase5_enterprise_iam.py tests/test_dynamic_dataset_evaluation.py tests/test_evaluation_datasets_persistence.py tests/test_predictive_action_control_engine.py tests/test_production_readiness.py tests/test_secret_rotation_and_session_invalidation.py tests/test_p0_security_remediation.py tests/test_platform_super_admin_license_suite.py -v
```

**Expected Result:**
```text
======================= 173 passed, 1 warning in 24.10s =======================
Exit Code: 0
```

### 2.2 Targeted Subsuite Execution

You can run individual test suites to test specific subsystems:

1. **IAM & Role Hierarchy:**
   ```bash
   python -m pytest tests/test_iam_role_matrix.py tests/test_iam_direct.py
   ```
2. **Predictive Action Control Engine (PACE):**
   ```bash
   python -m pytest tests/test_predictive_action_control_engine.py
   ```
3. **Platform Security & License Governance:**
   ```bash
   python -m pytest tests/test_platform_super_admin_license_suite.py
   ```
4. **Dynamic Dataset Evaluation:**
   ```bash
   python -m pytest tests/test_dynamic_dataset_evaluation.py
   ```

---

## 3. Frontend Quality & Build Verification

Execute frontend validation from the `frontend/` directory:

### Step 1: Type Checking

Validate that all TypeScript interfaces, component props, and route definitions compile cleanly:

```bash
cd frontend
npx tsc --noEmit
```

**Expected Result:** Exit code `0` (Zero compiler errors).

### Step 2: Code Linting

Verify ESLint standards:

```bash
npm run lint
```

### Step 3: Production Static Build

Verify that all 59 Next.js pages and routes compile and render:

```bash
npm run build
```

**Expected Result:** Output displays `59/59` static/SSG routes successfully generated with exit code `0`.

---

## 4. SDK Testing

### 4.1 TypeScript SDK Verification

From `sdks/typescript`:

```bash
cd sdks/typescript
npm run build
node tests/test_sdk.mjs
```

**Expected Result:** `5/5 tests passed` (Client creation, authorization headers, PACE evaluate simulation, error handling).

### 4.2 Python SDK Verification

From the repository root:

```bash
pip install -e sdks/python
python -m pytest backend/tests/test_sdk_suite.py -v
```

**Expected Result:** `19 passed` (Synchronous/Asynchronous clients, LangChain integration, CrewAI middleware, retry policies).

---

## 5. Git Formatting Verification

Before staging or committing any code or documentation:

```bash
git diff --check
```

Ensure this command exits with code `0`. Any trailing whitespace or malformed carriage return will be flagged for correction.
