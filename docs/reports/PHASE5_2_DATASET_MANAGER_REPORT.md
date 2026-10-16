# AGENTGUARD — PHASE 5.2: SIMULATION DATASET MANAGER & IAM ALIGNMENT REPORT

**Execution Date:** 2026-10-16  
**Status:** COMPLETE & VERIFIED  
**Repository:** `D:\AGENTGUARD`

---

## 1. Executive Summary

Phase 5.2 delivers an enterprise-grade **Dataset Manager** inside the AGENTGUARD Simulation Lab (`frontend/src/app/(app)/simulation/page.tsx`) and hardens the simulation dataset API endpoints with AGENTGUARD's authoritative **five-role enterprise IAM architecture**.

Authorized security engineers can now browse persisted evaluation datasets, upload and validate JSON benchmark files with client-side and server-side safety checks, inspect dataset records with ground truth notes, and review action-sequence timelines without triggering side effects.

Dataset-driven comparative evaluation is transparently surfaced: because arbitrary custom dataset execution requires scenario adapter compilation, the UI explicitly marks dataset-driven simulations as scheduled for Phase 6 rather than generating synthetic or misleading metrics.

All changes strictly conform to AGENTGUARD's design system, tenant isolation requirements, and regression benchmarks.

---

## 2. Five-Role Enterprise IAM Alignment

AGENTGUARD strictly adheres to its established five-role enterprise IAM model:
1. `ADMIN`
2. `MANAGER`
3. `SECURITY_OFFICER`
4. `AUDITOR`
5. `AGENT` (Machine Identity)

No secondary roles (e.g., `SUPER_ADMIN`, `SECURITY_ANALYST`, `DEVELOPER`, `OPERATOR`, `VIEWER`) were introduced or relied upon.

### Role Authorization Enforcement Matrix

| Enterprise Role | Role Type | List Datasets (`GET /eval-data`) | Inspect Details (`GET /eval-data/{name}`) | Import Datasets (`POST /eval-data/import`) | Backend HTTP Status / Message |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`ADMIN`** | Human | **ALLOWED** | **ALLOWED** | **ALLOWED** | `200 OK` / `201 Created` |
| **`MANAGER`** | Human | **ALLOWED** | **ALLOWED** | **ALLOWED** | `200 OK` / `201 Created` |
| **`SECURITY_OFFICER`** | Human | **ALLOWED** | **ALLOWED** | **ALLOWED** | `200 OK` / `201 Created` |
| **`AUDITOR`** | Human | **ALLOWED** | **ALLOWED** | **BLOCKED (Read-Only)** | `403 Forbidden`: *"AUDITOR role has read-only access and cannot import evaluation datasets"* |
| **`AGENT`** | Machine Identity | **BLOCKED** | **BLOCKED** | **BLOCKED** | `403 Forbidden`: *"AGENT represents an AI machine identity and cannot manage evaluation datasets"* |
| **Unauthenticated** | N/A | **BLOCKED** | **BLOCKED** | **BLOCKED** | `401 Unauthorized` |

### Security Invariants Enforced
- **Authoritative Server-Side Scoping:** The organization ID (`org_id`) is strictly extracted from `current_user.org_id`. Any `org_id` passed in request bodies is discarded.
- **Tenant Isolation:** Users in Organization Alpha cannot view or retrieve datasets belonging to Organization Beta (returns `404 Not Found`).
- **Namespace Scoping:** Datasets with identical names across distinct organizations coexist without conflict due to the database composite index on `(org_id, name)`.
- **Client Privilege Escalation Immunity:** Frontend role state is purely presentation-level; backend authorization endpoints remain authoritative and enforce all checks on every request.

---

## 3. Files Changed

### Backend
1. **`backend/routers/simulation.py`**
   - Explicitly configured `ENTERPRISE_EVAL_IMPORT_ROLES = {"ADMIN", "SECURITY_OFFICER", "MANAGER"}` and `ENTERPRISE_EVAL_READ_ROLES = {"ADMIN", "SECURITY_OFFICER", "MANAGER", "AUDITOR"}`.
   - Enforced strict `403 Forbidden` for `AUDITOR` attempting import and `AGENT` attempting management.
   - Fixed `org_id` derivation to guarantee tenant isolation across all dataset retrieval calls.

2. **`backend/tests/test_simulation_iam_alignment.py`** (New File)
   - 18 comprehensive integration tests validating API endpoints, role permissions, duplicate conflicts, malformed payload rejections, secret scanning, and cross-tenant boundaries.

### Frontend
1. **`frontend/src/app/(app)/simulation/page.tsx`**
   - Replaced placeholder simulation view with a multi-tab interface:
     - **Tab 1: Scenario Benchmarks** (existing 10 standard synthetic benchmark categories).
     - **Tab 2: Evaluation Datasets (Dataset Manager)**.
   - Added full Dataset Manager components:
     - **Dataset List Table:** Search filtering, record count badges, provenance tags, creation timestamps, and row selection.
     - **Empty, Loading, Error, and Permission-Denied States:** Informative banners with explicit role guidance.
     - **JSON Import Modal:** File picker, drag-and-drop, client-side `.json` and 5MB validation, payload structure preview, upload submission with duplicate name warnings, and automatic dataset list refreshing.
     - **Dataset Record Inspector:** Detailed record viewer displaying ground truth labels (`SAFE`/`RISKY`), provenance, agent profiles, action-sequence timelines, and audit notes without executing tools.
     - **Comparative Simulation Evaluation Card:** Clearly outlines the distinction between synthetic benchmark evaluations and dataset-driven evaluations, noting Phase 6 availability.

---

## 4. API Contracts Reused

No new API routes were created. All features reuse the durable Phase 5.1 endpoints:

### 1. `POST /api/simulation/eval-data/import`
- **Request:** `schemas.EvaluationDataImportRequest`
  - `dataset_name`: String (1-255 characters)
  - `description`: Optional String
  - `provenance`: Enum (`AUTHORIZED_LABELED_DATA`, `BENCHMARK_EVAL_FIXTURE`, `SYNTHETIC_EVAL_DATA`)
  - `records`: List of `EvaluationDatasetRecord` (1 to 500 records)
- **Response:** `schemas.EvaluationDataImportResponse`
  - `status`: `"SUCCESS"` or `"REJECTED"`
  - `dataset_name`: String
  - `provenance`: String
  - `imported_records_count`: Integer
  - `validation_errors`: List of Strings
  - `notice`: Provenance and isolation disclosure

### 2. `GET /api/simulation/eval-data`
- **Response:** `List[schemas.EvaluationDatasetSummary]`
  - `dataset_name`, `description`, `provenance`, `records_count`, `tags`, `created_at`

### 3. `GET /api/simulation/eval-data/{dataset_name}`
- **Response:** Full dataset payload including all records, action sequences, ground truth labels, and agent profiles.

---

## 5. Comparative Simulation Status & Technical Evaluation

### Can arbitrary evaluation datasets be simulated directly with the existing backend?
**No.** The current `SimulationRunner.execute_simulation_run` implementation in `backend/engines/simulation_engine.py` operates strictly on `VERSIONED_SIMULATION_SCENARIOS` (the 10 pre-compiled synthetic benchmark scenarios).

### UI Implementation
- Per strict instructions, **no metrics were faked or hallucinated**.
- The UI features a dedicated **"Comparative PACE Evaluation"** card explaining that custom dataset-driven evaluations are scheduled for Phase 6.
- A button to inspect the dataset records is provided so engineers can review the action sequences safely.

### Minimum Backend Changes Required for Phase 6 Dataset-Driven Evaluation:
1. **Dynamic Scenario Adapter:** Add a translation function `eval_record_to_simulation_scenario(record: EvaluationDatasetRecord) -> SimulationScenario`.
2. **Dataset-Scoped Run Parameter:** Extend `schemas.SimulationRunRequest` to accept an optional `dataset_name: Optional[str]` alongside `scenario_ids`.
3. **Execution Engine Routing:** In `simulation_runner.execute_simulation_run`, if `dataset_name` is supplied, query the persisted `EvaluationDatasetRecord` models for the authenticated `org_id`, convert them to transient scenarios, and execute the baseline-vs-PACE comparison against the recorded action sequences.

---

## 6. Verification & Automated Test Results

### 1. Dedicated Simulation IAM Alignment Suite
Command: `pytest backend/tests/test_simulation_iam_alignment.py -v`
```
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_01_api_integration_initial_list PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_02_admin_can_import_dataset PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_03_manager_can_import_dataset PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_04_security_officer_can_import_dataset PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_05_auditor_can_list_datasets PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_06_auditor_can_inspect_dataset_details PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_07_auditor_cannot_import_dataset PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_08_agent_machine_identity_cannot_import PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_09_agent_machine_identity_cannot_list_or_read PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_10_unauthenticated_request_rejected PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_11_forged_token_rejected PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_12_duplicate_dataset_import_conflict_rejection PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_13_malformed_dataset_invalid_ground_truth PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_14_malformed_dataset_missing_records PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_15_malformed_dataset_excessive_records PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_16_secret_scanning_rejects_credential_leak PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_17_cross_organization_tenant_isolation PASSED
backend/tests/test_simulation_iam_alignment.py::TestSimulationIAMAlignmentSuite::test_18_client_body_org_id_tampering_ignored PASSED

======================== 18 passed in 5.56s ========================
```

### 2. Persistent Evaluation Datasets Suite (Phase 5.1 Regression)
Command: `pytest backend/tests/test_evaluation_datasets_persistence.py -v`
```
======================== 11 passed in 4.86s ========================
```

### 3. PACE Simulation Lab Regression Suite
Command: `pytest backend/tests/test_pace_simulation_lab.py -v`
```
======================== 10 passed in 3.85s ========================
```

### 4. Predictive Action Control Engine Core Tests
Command: `pytest backend/tests/test_predictive_action_control_engine.py -q`
```
....................                                                     [100%]
======================== 20 passed in 5.41s ========================
```

### 5. Frontend TypeScript Compilation
Command: `npx tsc --noEmit` (in `frontend/`)
- **Result:** Exit code `0` (Zero type errors).

### 6. Frontend Production Build
Command: `npm run build` (in `frontend/`)
- **Result:** Exit code `0`. All 59 static routes generated cleanly.

---

## 7. Remaining Limitations & Recommendations

1. **Phase 6 Dynamic Simulation Runner:** As documented, the simulation execution runner currently evaluates static scenarios. Adding the adapter described in Section 5 will enable ad-hoc benchmark execution against custom datasets.
2. **Export / Download Feature:** Future iterations could allow authorized security engineers to export inspected evaluation datasets back into JSON format for offline benchmarking or external regulatory compliance reporting.
3. **Pagination for Ultra-Large Datasets:** Record inspection currently loads records for single datasets up to 500 records. If datasets exceed 500 records in later phases, cursor-based record pagination should be added to the GET endpoint.
