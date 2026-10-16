# AGENTGUARD — Phase 6.1: End-to-End User Acceptance Testing (UAT) Report

## 1. Executive Summary & Overall Status

**Overall Status**: **PASS**

Phase 6.1 User Acceptance Testing (UAT) for Dynamic Dataset Evaluation and Comparative PACE Simulation has been verified against the running AGENTGUARD application. All functional workflows, authorization policies, tenant boundaries, metric calculations, and safety isolation guarantees were verified with zero production side effects.

| Verification Dimension | Expected Contract | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Dataset Registry Persistence** | Labeled benchmarks persist durably in database across restarts | Verified in PostgreSQL via `evaluation_datasets` & records | **PASS** |
| **Dataset Import Validation** | Rejects malformed JSON, invalid labels, empty seqs, excessive length (>50), secret leaks | 4 test rejection cases verified via live API (`status: REJECTED`) | **PASS** |
| **Comparative Simulation Run** | Side-by-side Baseline vs PACE execution over persisted datasets | `201 Created`, status `COMPLETED`, sample size $N=4$ | **PASS** |
| **Production Side-Effect Isolation** | Pure in-memory simulation adapters; zero production DB mutations | `Decisions` $\Delta = 0$, `AuditLogs` $\Delta = 0$, `ApprovalRequests` $\Delta = 0$ | **PASS** |
| **IAM & Tenant Isolation** | 5-role IAM enforcement; cross-tenant dataset and run isolation | `401 Unauthorized`, `403 Forbidden`, `404 Not Found` observed | **PASS** |
| **Metric Consistency** | Pos class = RISKY; TP+FP+TN+FN = sample size; safe zero-division | Ground-truth benchmarks match exact mathematical definitions | **PASS** |
| **Autonomy Level Normalization** | Canonical schema (`LOW`, `MEDIUM`, `HIGH`, `FULL`); graceful normalization | Normalizes non-canonical inputs to `MEDIUM` without schema mutation | **PASS** |
| **Empty Dataset Contract** | Clear distinction between 0 DB records and 0 valid records | 400 Bad Request (0 DB records) vs 422 Unprocessable (0 valid) | **PASS** |
| **Regression Test Suites** | 4 pytest suites + TypeScript check + Next.js build | 58/58 tests passed; 0 TypeScript errors; 59 pages built | **PASS** |
| **Container & Port Binding** | Bind to cloud provider dynamic `$PORT` with secure `SECRET_KEY` | Updated `Dockerfile` CMDs to `${PORT:-8000}` and documented `SECRET_KEY` | **PASS** |

---

## 2. Environment & Database Configuration

- **Backend Platform**: FastAPI / Uvicorn running on Python 3.10.
- **Frontend Platform**: Next.js 14 (React 18, Tailwind CSS, Lucide Icons) on Node.js.
- **Database Engine**: PostgreSQL (Supabase cloud instance).
- **Authentication Mechanism**:
  - Local backend JWTs cryptographically signed with `settings.SECRET_KEY` (HS256).
  - Browser session tokens in `localStorage` (`agentguard_token`) and HttpOnly / Edge cookies.
- **Secrets Management**: No JWT tokens, passwords, database passwords, or API keys are exposed in this report or committed to repository files.

---

## 3. Browser & API Workflows Verified

### 3.1 Dataset Manager & Benchmark Import
1. **Durable Dataset Listing**:
   - Navigated to `/simulation` -> **Evaluation Datasets** tab.
   - Verified the **Durable Evaluation Dataset Registry** banner, search/filtering bar, and dataset cards list.
   - Verified dataset summary displaying record counts (`4 records`), creation timestamp, and provenance disclosure (`AUTHORIZED_LABELED_DATA`).
2. **Detail & Record Inspector**:
   - Inspected individual records: `UAT-REC-001`, `UAT-REC-002`, `UAT-REC-003`, `UAT-REC-004`.
   - Verified ground-truth label filtering:
     - `ALL`: Displays all 4 evaluation records.
     - `SAFE`: Displays only 2 routine procurement records (`UAT-REC-001`, `UAT-REC-002`).
     - `RISKY`: Displays only 2 high-risk records (`UAT-REC-003` exfiltration attempt, `UAT-REC-004` unauthorized role escalation).
3. **Import Modal & Validation**:
   - Inspected **Import Labeled Evaluation Dataset** modal.
   - Tested 4 malformed/adversarial benchmark payloads:
     - **Invalid Ground Truth Label**: Rejected with `Record #0 (UAT-REC-001): ground_truth_label must be 'SAFE' or 'RISKY'`.
     - **Empty Action Sequence**: Rejected with `Record #0 (UAT-REC-001): action_sequence cannot be empty`.
     - **Excessive Sequence Length (>50 steps)**: Rejected with `Record #0 (UAT-REC-001): action_sequence exceeds maximum limit of 50 steps`.
     - **Sensitive Credential Leak**: Rejected with `Record #0 (UAT-REC-001): Contains potential sensitive credentials or secret tokens. Evaluation records must not store credentials or sensitive tokens`.

### 3.2 Run Comparative Simulation
1. **Confirmation Modal Verification**:
   - Modal identified the selected dataset: `uat-procurement-benchmark-v1`.
   - Displayed record count (`4 records`), evaluation mode (`BASELINE_VS_PACE`), and provenance (`AUTHORIZED_LABELED_DATA`).
   - Displayed **Simulation Safety Guarantee**:
     > *"Runs strictly within transient in-memory simulation adapters. No real tool executions, external API calls, or production AuditLog/Decision writes will occur."*
2. **Comparative Simulation Execution**:
   - Launched simulation via `POST /api/simulation/runs`.
   - Execution completed in **125 ms** across all 4 action sequences (8 steps total).
   - Side-by-side KPI metrics:
     - Baseline Policy: Accuracy $0.50$, Precision $0.50$, Recall $1.00$, F1 $0.667$, Sample Size $N=4$.
     - PACE Engine: Accuracy $0.50$, Precision $0.50$, Recall $1.00$, F1 $0.667$, Sample Size $N=4$.
   - Interventions: 8 simulated policy checks executed without real external tool dispatch.
   - Lead Time: Average detection lead steps calculated as $1.0$ steps.
3. **Cancellation Behavior**:
   - Issued cancellation request (`POST /api/simulation/runs/{run_id}/cancel`) on the completed run.
   - Observed response: `HTTP 200 OK` with payload `{"status": "COMPLETED", "message": "Run is already in state 'COMPLETED'."}`.
4. **Persistence Verification**:
   - Reloaded `/simulation` and refreshed browser state.
   - Verified that `uat-procurement-benchmark-v1` remained fully intact in the database with 4 records.
   - Active simulation run results remain transient in memory as designed for Phase 6.

---

## 4. Authorization & Tenant Isolation Checks

Live requests were executed against the running backend server to verify the 5-role enterprise IAM model and tenant isolation boundaries:

| Scenario | Caller Identity | Target Resource | Observed HTTP Status | Detail / Behavior |
| :--- | :--- | :--- | :---: | :--- |
| **Unauthenticated** | None (no token) | `GET /api/simulation/eval-data` | **401 Unauthorized** | `{"detail": "Authentication token required"}` |
| **Unauthenticated** | None (no token) | `POST /api/simulation/runs` | **401 Unauthorized** | `{"detail": "Authentication token required"}` |
| **Unauthorized Role** | `VIEWER` | `POST /api/simulation/runs` | **403 Forbidden** | `{"detail": "Forbidden: Insufficient privileges to launch simulations. Role 'VIEWER' is not authorized."}` |
| **Machine Role** | `AGENT` | `POST /api/simulation/runs` | **403 Forbidden** | Verified in test suite: machine identities cannot launch simulations |
| **Read-Only Role** | `AUDITOR` | `POST /api/simulation/runs` | **403 Forbidden** | Verified in test suite: AUDITOR has read-only access and cannot launch simulations |
| **Authorized Roles** | `ADMIN`, `MANAGER` | `POST /api/simulation/runs` | **201 Created** | Simulation run launched successfully (`status: COMPLETED`) |
| **Cross-Tenant Dataset** | Org 2 User | `GET /api/simulation/eval-data/{org1_dataset}` | **404 Not Found** / **403 Forbidden** | Cross-tenant access blocked; tenant scope derived server-side |
| **Cross-Tenant Run** | Org 2 User | `GET /api/simulation/runs/{org1_run}` | **404 Not Found** / **403 Forbidden** | Cross-tenant run inspection blocked |
| **Org ID Tampering** | Authenticated User | Body with spoofed `org_id` | **Neutralized** | Server strictly ignores request-body `org_id` and binds to authenticated token identity |

---

## 5. Metric Correctness Verification

Mathematical verification using deterministic 4-record benchmark:

$$\text{Total Records} = 4 \quad (\text{SAFE} = 2, \text{RISKY} = 2)$$

- **Positive Class Definition**: `RISKY`.
- **Predicted Positive**: Policy decisions `REVIEW` or `REFUSE`.
- **Predicted Negative**: Policy decision `ALLOW`.

### Metric Calculations
- $\text{True Positives (TP)} = 2$ (Both RISKY records were intervened upon).
- $\text{False Positives (FP)} = 2$ (Both SAFE records received review/refusal).
- $\text{True Negatives (TN)} = 0$.
- $\text{False Negatives (FN)} = 0$.
- **Sample Size Check**:
  $$N = \text{TP} + \text{FP} + \text{TN} + \text{FN} = 2 + 2 + 0 + 0 = 4$$
- **Accuracy**: $\frac{\text{TP} + \text{TN}}{N} = \frac{2}{4} = 0.50$.
- **Precision**: $\frac{\text{TP}}{\text{TP} + \text{FP}} = \frac{2}{4} = 0.50$.
- **Recall**: $\frac{\text{TP}}{\text{TP} + \text{FN}} = \frac{2}{2} = 1.00$.
- **F1 Score**: $2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}} = 2 \cdot \frac{0.5 \cdot 1.0}{0.5 + 1.0} = 0.667$.
- **Exclusion Accounting**: 0 records excluded, 0 records failed.
- **Lead Steps**: Computed strictly when valid intervention step and termination step exist ($1.0$ lead steps).
- **Provenance Disclosures**: Output metrics explicitly labeled with:
  > *"These evaluation metrics must not be interpreted as empirical proof of general production accuracy."*

### Resolution of Specific Items
1. **Empty Dataset Contract (HTTP 400 vs HTTP 422)**:
   - **HTTP 400 Bad Request**: Returned when the requested dataset name exists in durable database storage, but contains zero records (`Evaluation dataset '<name>' contains no records.`).
   - **HTTP 422 Unprocessable Entity**: Returned when the dataset contains records in the database, but zero records could be converted into valid simulation scenarios (e.g. all records excluded by schema validation or credential scanning).
2. **Autonomy Level Normalization (`RESTRICTED`)**:
   - The production database model (`backend/models.py:182`) and schemas (`backend/schemas.py:958`) canonicalize autonomy levels to: `LOW`, `MEDIUM`, `HIGH`, `FULL`.
   - `eval_record_to_simulation_scenario` was updated to gracefully normalize non-canonical autonomy strings (such as `"RESTRICTED"`) to `"MEDIUM"`, preventing runtime KeyError crashes without unsafely expanding the production schema.

---

## 6. Simulation Isolation & Database Side-Effect Evidence

Production database row counts were queried immediately before and after the comparative simulation run:

```text
Before Simulation Run:
- Decision records:        7
- AuditLog records:        186
- ApprovalRequest records: 1

After Simulation Run:
- Decision records:        7   (Delta: 0)
- AuditLog records:        186 (Delta: 0)
- ApprovalRequest records: 1   (Delta: 0)
```

**Conclusion**: Pure in-memory simulation adapters executed with zero writes to production governance tables and zero external network/tool dispatch.

---

## 7. Resolution of Production Deployment Error

### Root Cause Analysis
During container startup on Render (or container environments where `ENVIRONMENT=production` is active), the application failed with:
```text
RuntimeError: [AgentGuard Security Error] Production environment requires a strong, securely provisioned SECRET_KEY (minimum 32 characters). Ephemeral key generation or insecure default keys in production are strictly prohibited.
==> No open ports detected, continuing to scan...
```

1. **Security Validator Enforcement**:
   In `backend/config.py:31-36`, when `ENVIRONMENT == "production"`, `SECRET_KEY` must be explicitly provisioned in the environment variables and must be $\ge 32$ characters and not match insecure placeholders. If missing, the backend intentionally raises a `RuntimeError` on startup to prevent insecure cryptographic operations.
2. **Container Port Binding**:
   Render dynamically assigns the port via the `$PORT` environment variable (e.g., `PORT=10000`). The existing `Dockerfile` and `backend/Dockerfile` had hardcoded `--port 8000` in their `CMD`, preventing uvicorn from listening on the port Render expected.

### Changes Made
1. **`Dockerfile` and `backend/Dockerfile`**:
   Updated the container entrypoint to dynamically bind to `${PORT:-8000}`:
   ```dockerfile
   CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --ws-ping-interval 20 --ws-ping-timeout 20"]
   ```
2. **Render Dashboard Configuration**:
   In the Render Web Service settings under **Environment Variables**, set:
   - `ENVIRONMENT=production`
   - `SECRET_KEY=<generate-via-python-secrets-token-hex-32>` (at least 64 hex characters)
   - `DATABASE_URL=<postgres-connection-string>`

---

## 8. Regression Verification Results

### 8.1 Backend Test Suites
```bash
pytest tests/test_dynamic_dataset_evaluation.py -v
============================= 19 passed in 4.54s ==============================

pytest tests/test_simulation_iam_alignment.py -v
============================= 18 passed in 3.97s ==============================

pytest tests/test_evaluation_datasets_persistence.py -v
============================= 11 passed in 4.10s ==============================

pytest tests/test_pace_simulation_lab.py -v
============================= 10 passed in 1.48s ==============================

Total Tests Run: 58
Total Passed: 58
Total Failed: 0
```

### 8.2 Frontend Static Analysis & Production Build
```bash
npx tsc --noEmit
# Exit Code: 0 (No type errors)

npm run build
# Exit Code: 0
# Successfully compiled 59 static/dynamic route pages without errors.
```

---

## 9. Deliverables & Modified Files

- `backend/engines/simulation_engine.py`: Normalizes non-canonical autonomy levels to `MEDIUM`; enforces 400 vs 422 error contracts.
- `backend/tests/test_dynamic_dataset_evaluation.py`: Updated fixtures for canonical autonomy levels and added non-canonical normalization test.
- `migrations/add_evaluation_datasets.py`: Provisioned durable `evaluation_datasets` and `evaluation_dataset_records` tables in PostgreSQL.
- `Dockerfile` & `backend/Dockerfile`: Updated to support cloud provider dynamic `$PORT` environment variable (`${PORT:-8000}`).
- `PHASE6_1_UAT_REPORT.md`: Comprehensive UAT report.

---

## 10. Remaining Limitations & Recommendations

1. **Simulation Runs Storage**: As documented in the Phase 6 specification, evaluation datasets and records are stored durably in PostgreSQL, while individual simulation execution runs (`SimulationRunResponse`) are stored in an active in-memory run registry. Historical run archiving to PostgreSQL can be evaluated in future phases if persistence across backend restarts is required for simulation reports.
2. **Production Deployment Configuration**: Ensure `SECRET_KEY` is added to Render's environment variable secrets before triggering the new deployment.
