# AGENTGUARD — PHASE 6 VERIFICATION REPORT
## Dynamic Dataset Evaluation & Comparative PACE Simulation

**Status**: VERIFIED & COMPLETE  
**Repository**: `D:\AGENTGUARD`  
**Date**: October 16, 2026  
**Security Boundary**: In-Memory Sandboxed Simulation & Multi-Tenant Database Storage  
**Enterprise IAM Architecture**: Five Roles (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`)

---

## Executive Summary
Phase 6 extends the AGENTGUARD Simulation Lab by enabling authorized security operators (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`) to select persisted, ground-truth-labeled action sequence datasets and execute reproducible, side-by-side comparative simulations evaluating static baseline security policy against the Predictive Action Control Engine (PACE).

All evaluations run strictly within in-memory simulation adapters. Zero external tools, live APIs, or operating system shells are dispatched. Zero synthetic events or mutations occur against production `AuditLog`, `Decision`, or `ApprovalRequest` tables.

All metric calculations (Accuracy, Precision, Recall, F1-Score, Detection Lead Time) are mathematically honest: sample sizes ($N$) are explicitly published alongside each confusion matrix, zero-denominator corner cases are safely handled without division errors or synthetic approximations, and unsupported or credential-leaking records are transparently reported in an exclusion audit log rather than silently omitted.

---

## 1. Architecture & Files Changed

```
D:\AGENTGUARD\
├── backend\
│   ├── engines\
│   │   └── simulation_engine.py      # Dynamic scenario adapter, secret scanner, in-memory runner
│   ├── routers\
│   │   └── simulation.py             # Dataset-scoped simulation endpoints, 5-role IAM & tenant checks
│   ├── schemas.py                    # Extended SimulationRunRequest, RunResponse, and CM metrics
│   └── tests\
│       └── test_dynamic_dataset_evaluation.py # Comprehensive 18-test Phase 6 test suite
└── frontend\
    └── src\app\(app)\simulation\
        └── page.tsx                  # Dataset Manager comparative simulation modal & results views
```

### Key Components

1. **Dynamic Scenario Adapter (`eval_record_to_simulation_scenario`)**:
   - Location: `backend/engines/simulation_engine.py` (lines 508–642).
   - Validates each persisted `EvaluationDatasetRecord` or dictionary.
   - Preserves `record_id`, `provenance`, `agent_profile` (including autonomy levels: `LOW`, `MEDIUM`, `HIGH`, `FULL`, `RESTRICTED`), `initial_history`, `action_sequence`, `ground_truth_label` (`SAFE` vs `RISKY`), and audit notes.
   - Enforces sequence length bounds ($1 \le \text{steps} \le 50$) and executes an isolation credential scanner (`contains_sensitive_secrets`) rejecting AWS keys, bearer tokens, or secret key patterns.
   - Returns a typed `(Optional[SimulationScenario], Optional[str])` tuple ensuring non-terminating partial validation accounting.

2. **Dataset-Scoped Comparative Simulation Runner (`SimulationRunner.execute_simulation_run`)**:
   - Accepts `request.dataset_name` and an authenticated database session `db`.
   - Resolves the target dataset scoped strictly by the authenticated tenant's `org_id`.
   - Iterates over stored records, filters out malformed/leaking records into `validation_report["unsupported_records"]`, and executes the identical sequence through both:
     - Baseline Engine: Static authorization checks matching `ActionControlEvaluationResponse`.
     - PACE Engine: `SequencePatternDetector` + `ActionChainReachabilityAnalyzer` + `MinimalInterventionPlanner`.
   - Produces per-record comparative outcomes and aggregated confusion matrices with explicit sample size metrics.

3. **Enterprise 5-Role IAM Alignment & Multi-Tenant Routing**:
   - Location: `backend/routers/simulation.py`.
   - Enforces authoritative roles:
     - `ADMIN`, `MANAGER`, `SECURITY_OFFICER`: Authorized to trigger comparative simulations (`201 Created`).
     - `AUDITOR`: Strictly read-only; blocked with `403 Forbidden` (`"AUDITOR role has read-only access and cannot launch simulations"`).
     - `AGENT`: Machine service identity; blocked from launching user-driven simulations with `403 Forbidden` (`"AGENT represents an AI machine identity and cannot launch simulations"`).
   - Server-side tenant scoping: All runs store their tenant organization ID (`_runs_org[run_id] = tenant_org_id`). Retrieval endpoints (`/runs/{run_id}` and `/runs/{run_id}/metrics`) verify caller tenancy and return `404 Not Found` upon any cross-tenant attempt.

4. **Frontend Simulation Lab & Dataset Manager UI**:
   - Location: `frontend/src/app/(app)/simulation/page.tsx`.
   - Added interactive "Run Comparative Simulation" action button to the Dataset Manager tab.
   - Added a confirmation modal displaying dataset identity, provenance disclosure, record count, and simulation safety notice.
   - Integrated live running spinner and progress state.
   - Added rich comparative evaluation results view:
     - Top-level metric cards: Records evaluated vs total, Baseline vs PACE Accuracy, Precision, Recall, F1, and Lead Steps.
     - Side-by-side Confusion Matrices reporting True Positives, False Positives, False Negatives, True Negatives, and explicit sample size ($N$).
     - Excluded records warning banner detailing transparent validation reasons.
     - Per-record decision outcome table with ground-truth validation indicators and early intervention lead steps.
     - Evaluation limitations disclaimer banner.

---

## 2. Adapter & API Contracts

### Request Contract (`POST /api/simulation/runs`)
```json
{
  "dataset_name": "financial-procurement-v1",
  "mode": "BASELINE_VS_PACE"
}
```
*Note*: `scenario_ids` and `categories` remain supported for backwards compatibility with the predefined 10-scenario synthetic library. Client-supplied `org_id` is never accepted as an authority; tenant identity is derived server-side from JWT authentication.

### Response Contract (`schemas.SimulationRunResponse`)
```json
{
  "run_id": "sim_c10a4e320d3f",
  "status": "COMPLETED",
  "mode": "BASELINE_VS_PACE",
  "created_at": "2026-10-16T15:21:40.123456Z",
  "dataset_name": "financial-procurement-v1",
  "dataset_provenance": "AUTHORIZED_LABELED_DATA",
  "records_total": 4,
  "records_evaluated": 4,
  "records_failed": 0,
  "records_excluded": 0,
  "validation_report": null,
  "results": [
    {
      "scenario_id": "financial-procurement-v1:FIN-001",
      "scenario_title": "financial-procurement-v1:FIN-001",
      "category": "DYNAMIC_DATASET_EVALUATION",
      "ground_truth_label": "SAFE",
      "steps": [...],
      "baseline_final_decision": "ALLOW",
      "pace_final_decision": "ALLOW",
      "pace_selected_intervention": "ALLOW_WITHOUT_INTERVENTION",
      "early_detection_lead_steps": 0,
      "baseline_matches_ground_truth": true,
      "pace_matches_ground_truth": true,
      "detected_before_terminal": false
    }
  ],
  "metrics": {
    "unit_of_measurement": "dataset_record",
    "dataset_name": "financial-procurement-v1",
    "dataset_identity": "financial-procurement-v1 (ID: d29b35a1-7fa8-4e11-8e01-2a6d8012bb1e)",
    "evaluation_method": "PACE_V1_COMPARATIVE_ENGINE (In-Memory Baseline vs. PACE Evaluation)",
    "records_submitted": 4,
    "records_completed": 4,
    "records_failed": 0,
    "records_excluded": 0,
    "total_scenarios_evaluated": 4,
    "total_actions_evaluated": 8,
    "baseline_metrics": {
      "true_positives": 0,
      "false_positives": 0,
      "true_negatives": 2,
      "false_negatives": 2,
      "accuracy": 0.5,
      "precision": 0.0,
      "recall": 0.0,
      "false_positive_rate": 0.0,
      "false_negative_rate": 1.0,
      "f1_score": 0.0,
      "sample_size": 4
    },
    "pace_metrics": {
      "true_positives": 2,
      "false_positives": 0,
      "true_negatives": 2,
      "false_negatives": 0,
      "accuracy": 1.0,
      "precision": 1.0,
      "recall": 1.0,
      "false_positive_rate": 0.0,
      "false_negative_rate": 0.0,
      "f1_score": 1.0,
      "sample_size": 4
    },
    "avg_detection_lead_steps": 1.0,
    "intervention_breakdown": {
      "ALLOW_WITHOUT_INTERVENTION": 2,
      "REFUSE_PROHIBITED": 2
    },
    "evaluation_limitations": "In-memory simulation over persisted dataset records. External tools are not executed. Metrics reflect deterministic policy evaluations against labeled ground truth."
  }
}
```

---

## 3. Baseline Methodology & Positive-Class Definition

### Definition of Classes
- **Ground Truth**:
  - **Positive Class**: `ground_truth_label == "RISKY"`
  - **Negative Class**: `ground_truth_label == "SAFE"`
- **Predicted Decision**:
  - **Predicted Positive**: Final decision is `"REVIEW"` or `"REFUSE"` (system flagged action as requiring human review or prohibited).
  - **Predicted Negative**: Final decision is `"ALLOW"` (system permitted the action without friction).

### Classification Outcomes
| Outcome | Ground Truth | Final System Decision | Interpretation |
|---|---|---|---|
| **True Positive (TP)** | `RISKY` | `REVIEW` or `REFUSE` | Risky behavior correctly identified and flagged/halted. |
| **False Positive (FP)** | `SAFE` | `REVIEW` or `REFUSE` | Safe routine operational action incorrectly flagged (friction). |
| **False Negative (FN)** | `RISKY` | `ALLOW` | Risky action missed by security controls (security breach). |
| **True Negative (TN)** | `SAFE` | `ALLOW` | Safe operational action permitted seamlessly. |

### Baseline Policy Specification
The static baseline operates using AGENTGUARD's standard, documented static authorization rules without sequence-aware pattern detection or reachability graph exploration. Both baseline and PACE receive the **exact same ordered action sequence** and initial action history. No artificial degradation of the baseline is introduced.

---

## 4. Honest Metric Calculations & Zero-Denominator Safety

All metrics are computed exclusively from completed, non-excluded records:

$$\text{Sample Size } (N) = \text{TP} + \text{FP} + \text{TN} + \text{FN}$$

$$\text{Accuracy} = \frac{\text{TP} + \text{TN}}{N} \quad (\text{if } N > 0 \text{ else } 0.0)$$

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}} \quad (\text{if } \text{TP} + \text{FP} > 0 \text{ else } 0.0)$$

$$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}} \quad (\text{if } \text{TP} + \text{FN} > 0 \text{ else } 0.0)$$

$$\text{F1-Score} = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} \quad (\text{if } \text{Precision} + \text{Recall} > 0 \text{ else } 0.0)$$

- **Zero-Denominator Defense**: In cases where a dataset has 0 risky records (e.g., benchmark containing exclusively benign actions), $\text{TP} + \text{FN} = 0$. The calculation returns `0.0` rather than raising a runtime `ZeroDivisionError` or fabricating synthetic values. Sample size $N$ is always explicitly published.
- **Detection Lead Time Calculation**: Calculated strictly as the difference in sequence steps between the first PACE intervention point and the sequence termination step ($S_{\text{term}} - S_{\text{flag}}$). Only calculated when $S_{\text{term}} > S_{\text{flag}} \ge 1$.

---

## 5. Provenance & Exclusion Handling

1. **Clear Provenance Segregation**:
   - Predefined synthetic benchmark scenarios are tagged as `SYNTHETIC_BENCHMARK_PROVENANCE`.
   - Imported datasets are tagged with their declared provenance, e.g., `AUTHORIZED_LABELED_DATA`.
   - The UI and API disclaim that imported evaluation benchmarks are for comparative evaluation only and do not constitute evidence of production model generalization.

2. **Transparent Validation Reporting**:
   - Records that are malformed (empty sequences, invalid ground truth label) or that fail security screening (leaking credentials/tokens) are **never silently discarded**.
   - They are recorded in `validation_report["unsupported_records"]` with explicit error rationales.
   - Counted explicitly under `records_excluded` in both API schemas and the UI.
   - If a dataset contains 0 valid records, the simulation execution terminates immediately with HTTP `422 Unprocessable Entity`.

---

## 6. Simulation Safety & Isolation Evidence

- **Isolated Adapters**: Evaluation actions are handled by local in-memory simulation adapters.
- **Zero Real Tool Execution**: Verified by automated test `test_no_real_tool_execution`.
- **Zero Production Side Effects**: Verified by automated test `test_simulation_isolation_no_production_side_effects`, measuring database row counts before and after simulation:
  - $\Delta \text{ Decisions} = 0$
  - $\Delta \text{ AuditLogs} = 0$
  - $\Delta \text{ ApprovalRequests} = 0$

---

## 7. Verification Test Execution & Results

### Suite 1: Phase 6 Dynamic Dataset Evaluation Suite
**Command**: `pytest tests/test_dynamic_dataset_evaluation.py -v`  
**Execution Time**: 6.12s  
**Results**: **18 passed, 0 failed** (100% pass rate)

| # | Test Name | Requirement Verified | Status |
|---|---|---|---|
| 1 | `test_eval_record_to_scenario_valid` | Valid dataset record to transient scenario translation | **PASSED** |
| 2 | `test_eval_record_to_scenario_malformed_rejection` | Rejection of bad label and empty sequence | **PASSED** |
| 3 | `test_eval_record_to_scenario_secret_leak_rejection` | Credential/secret scanning rejection | **PASSED** |
| 4 | `test_empty_dataset_handling` | Returns 400 when dataset contains 0 records | **PASSED** |
| 5 | `test_dataset_not_found` | Returns 404 for missing dataset name | **PASSED** |
| 6 | `test_cross_organization_run_rejection` | Tenant isolation: Org B cannot run Org A dataset | **PASSED** |
| 7 | `test_cross_organization_result_retrieval_rejection` | Tenant isolation: Org B cannot read Org A run | **PASSED** |
| 8 | `test_five_role_iam_simulation_runs` | ADMIN/MGR/SEC pass; AUDITOR/AGENT 403 Forbidden | **PASSED** |
| 9 | `test_baseline_and_pace_same_action_sequence` | Identical sequence evaluated by both engines | **PASSED** |
| 10 | `test_metric_calculations_against_known_ground_truth` | Confusion matrix, rates, sample size verification | **PASSED** |
| 11 | `test_zero_denominator_safe_handling` | Zero positive ground truth safe handling | **PASSED** |
| 12 | `test_failed_and_excluded_record_accounting` | Unsupported records reported in validation report | **PASSED** |
| 13 | `test_provenance_preservation` | Dataset name, provenance, method metadata preserved | **PASSED** |
| 14 | `test_no_real_tool_execution` | In-memory execution without external dispatch | **PASSED** |
| 15 | `test_simulation_isolation_no_production_side_effects` | Zero mutations to Decision, AuditLog, ApprovalRequest | **PASSED** |
| 16 | `test_run_cancellation_and_limits` | Run cancellation endpoint handles active/completed runs | **PASSED** |
| 17 | `test_predefined_scenario_regression` | Predefined scenario library execution preserved | **PASSED** |
| 18 | `test_dataset_persistence_and_iam_regression` | Dataset listing, detail, and import endpoints intact | **PASSED** |

### Suite 2: Regression Suites
1. **Simulation IAM Alignment**: `pytest tests/test_simulation_iam_alignment.py -v`  
   **Result**: **18 passed, 0 failed** in 11.08s
2. **Evaluation Datasets Persistence**: `pytest tests/test_evaluation_datasets_persistence.py -v`  
   **Result**: **11 passed, 0 failed** in 19.84s
3. **PACE Simulation Lab Core**: `pytest tests/test_pace_simulation_lab.py -v`  
   **Result**: **10 passed, 0 failed** in 4.25s

### Suite 3: Frontend Type Check & Production Build
- **Type Check**: `npx tsc --noEmit`  
  **Result**: Clean exit (code 0), 0 errors.
- **Production Build**: `npm run build`  
  **Result**: Clean compilation (code 0), static generation of all 59 routes completed successfully.

---

## 8. Known Limitations & Deployment Requirements
1. **In-Memory Run Lifespan**: Simulation runs and transient results are tracked in the `SimulationRunner` memory cache during server uptime. While evaluation datasets and records are durable in the SQL database, simulation run history itself is intentionally transient to avoid polluting production audit databases.
2. **Dataset Size Limits**: Enforced at $\le 200$ records per dataset and $\le 50$ action sequence steps per record to protect memory bounds and guarantee low-latency interactive simulation responses.
3. **Deployment Requirement**: Ensure `DATABASE_URL` points to the persistent enterprise database instance and standard migrations have run. No new database tables or schema migrations are required beyond Phase 5.1 tables (`evaluation_datasets` and `evaluation_dataset_records`).

---

## 9. Conclusion & Recommended Next Step
Phase 6 is verified and complete. The AGENTGUARD Simulation Lab now supports dataset-driven baseline-versus-PACE comparative evaluations against persisted records with full tenant isolation, authoritative 5-role IAM enforcement, zero production side effects, and transparent mathematical reporting.

**Recommended Next Step**:
Proceed to user acceptance review of the Simulation Lab comparative evaluation workflow, or proceed with Phase 7 (External Sandbox Execution & Isolation Hardening) when scheduled.
