# AGENTGUARD — PHASE 5.1: PERSISTENT SIMULATION EVALUATION DATASETS REPORT

## Executive Summary
In AGENTGUARD Phase 5.1, the Simulation & Evaluation Lab's in-memory dataset storage (`SimulationRunner._evaluation_datasets`) was upgraded to durable, database-backed storage. Authorized, labeled action-sequence evaluation datasets now survive backend process restarts and database session lifecycles. All existing Predictive Action Control Engine (PACE) behavior, simulation guardrails, API contracts, tenant-isolation guarantees, and frontend integrations are preserved without regression.

---

## 1. Existing Architecture Inspected
Before making code changes, the existing repository architecture was thoroughly inspected:
- **`backend/engines/simulation_engine.py`**: Contained `SimulationRunner` with an in-memory dictionary `self._evaluation_datasets: Dict[str, Dict[str, Any]]`. While simulation runs appropriately execute in memory, imported evaluation datasets were volatile and lost on backend restarts.
- **`backend/routers/simulation.py`**: Exposed `/simulation/eval-data/import`, `/simulation/eval-data`, and `/simulation/eval-data/{dataset_name}` delegating directly to the in-memory runner without injecting database sessions or applying tenant filtering on queries.
- **`backend/schemas.py`**: Defined Pydantic schemas `EvaluationDataImportRequest`, `EvaluationDatasetRecord`, `EvaluationDataImportResponse`, and `EvaluationDatasetSummary`.
- **`backend/models.py`**: Base SQLAlchemy architecture utilizing platform-independent `GUID` (PostgreSQL UUID / SQLite CHAR(36)), explicit `org_id` foreign keys, JSON columns for complex payloads, and multi-column indexes.
- **`backend/database.py` & `backend/bootstrap.py`**: Engine initialization with `AUTO_BOOTSTRAP_DB`, idempotent table creation via `Base.metadata.create_all`, and backward-compatible non-destructive column inspection (`ensure_schema_compatibility`).
- **`backend/migrations/`**: Contained `cleanup_and_deduplicate.py` and `rls_tenant_policies.sql`.

---

## 2. Storage Design and Migration Approach

### Data Models (`backend/models.py`)
Two database models were introduced:

1. **`EvaluationDataset` (`evaluation_datasets`)**:
   - `id`: `GUID` primary key.
   - `org_id`: `GUID` foreign key referencing `organizations.id` with indexing.
   - `name`: `String(255)` dataset name.
   - `description`: `Text` optional description.
   - `provenance`: `String(100)` (e.g. `AUTHORIZED_LABELED_DATA`, `BENCHMARK_EVAL_FIXTURE`, `SYNTHETIC_EVAL_DATA`).
   - `records_count`: `Integer` cached count of records for fast listing without loading sequence trees.
   - `tags`: `JSON` array of unique tags across all records in the dataset.
   - `metadata_json`: `JSON` object for import provenance tracking.
   - `created_at` / `updated_at`: `DateTime` timestamps (UTC).
   - **Constraints & Indexes**:
     - `UniqueConstraint("org_id", "name", name="uq_evaluation_datasets_org_name")`: Enforces unique dataset name per tenant organization.
     - `Index("ix_evaluation_datasets_org_name", "org_id", "name")`.
     - `Index("ix_evaluation_datasets_org_created", "org_id", "created_at")`.

2. **`EvaluationDatasetRecord` (`evaluation_dataset_records`)**:
   - `id`: `GUID` primary key.
   - `dataset_id`: `GUID` foreign key referencing `evaluation_datasets.id` with `ondelete="CASCADE"`.
   - `org_id`: `GUID` foreign key referencing `organizations.id` for row-level tenant security.
   - `record_id`: `String(100)` unique identifier per record within the dataset (e.g. `REC-ALPHA-001`).
   - `provenance`: `String(100)`.
   - `agent_profile`: `JSON` serialized agent configuration (`ScenarioAgentProfile`).
   - `initial_history`: `JSON` list of past action trace events.
   - `action_sequence`: `JSON` list of evaluated actions (`ScenarioActionStep`).
   - `ground_truth_label`: `String(50)` (`SAFE` or `RISKY`).
   - `ground_truth_notes`: `Text` audit or evaluation rationale.
   - `tags`: `JSON` list of tags.
   - `created_at`: `DateTime` timestamp.
   - **Constraints & Indexes**:
     - `UniqueConstraint("dataset_id", "record_id", name="uq_eval_record_dataset_record_id")`.
     - `Index("ix_eval_records_dataset_record", "dataset_id", "record_id")`.
     - `Index("ix_eval_records_org_label", "org_id", "ground_truth_label")`.

### Migration Strategy
- **Idempotent Bootstrapping**: `Base.metadata.create_all(bind=engine)` automatically provisions the new tables on service start without dropping existing tables or erasing records.
- **Schema Compatibility**: Added column validation checks in `backend/bootstrap.py:ensure_schema_compatibility` to safely verify schema state.
- **Standalone Migration Script**: Created `backend/migrations/add_evaluation_datasets.py` for independent execution.
- **PostgreSQL RLS Policies**: Added tenant isolation RLS policies to `backend/migrations/rls_tenant_policies.sql`.

---

## 3. Files Changed
1. `backend/models.py`:
   - Added `UniqueConstraint` to imports.
   - Added `evaluation_datasets` relationship to `Organization`.
   - Added `EvaluationDataset` and `EvaluationDatasetRecord` declarative models.
2. `backend/bootstrap.py`:
   - Added table column compatibility inspection for `evaluation_datasets` in `ensure_schema_compatibility`.
3. `backend/engines/simulation_engine.py`:
   - Implemented secret and token scanning (`contains_sensitive_secrets`) to block credentials, API keys (`bearer `, `sk-`, `ag_live_`), and private keys from evaluation records.
   - Updated `import_evaluation_dataset` to transactionally validate bounds, detect duplicates, and persist datasets to the database.
   - Updated `list_evaluation_datasets` and `get_evaluation_dataset` to query database models with organization scoping.
   - Removed the volatile `self._evaluation_datasets` in-memory dictionary.
4. `backend/routers/simulation.py`:
   - Injected `db: Session = Depends(get_db)` into evaluation endpoints.
   - Added role-based authorization: importing restricted to `SUPER_ADMIN`, `ADMIN`, `SECURITY_ANALYST`, `DEVELOPER`, `OPERATOR`, `MANAGER`.
   - Derived tenant scope strictly from `current_user.org_id` (never trusted from request body).
5. `backend/migrations/add_evaluation_datasets.py`:
   - Standalone migration runner for manual or deployment pipeline migrations.
6. `backend/migrations/rls_tenant_policies.sql`:
   - Added RLS policies for `evaluation_datasets` and `evaluation_dataset_records`.
7. `backend/tests/test_evaluation_datasets_persistence.py`:
   - Comprehensive 11-test automated suite covering all Phase 5.1 requirements.

---

## 4. API Compatibility Details
The external HTTP contracts were preserved 100%:
- `POST /api/simulation/eval-data/import`: Returns `201 Created` with `schemas.EvaluationDataImportResponse` (`status="SUCCESS"` on valid import, `status="REJECTED"` with `validation_errors` on duplicate or malformed input).
- `GET /api/simulation/eval-data`: Returns `200 OK` with `List[schemas.EvaluationDatasetSummary]` (`dataset_name`, `description`, `provenance`, `records_count`, `created_at`, `tags`).
- `GET /api/simulation/eval-data/{dataset_name}`: Returns `200 OK` with dataset details and records (`dataset_name`, `description`, `provenance`, `records`, `created_at`, `tags`), or `404 Not Found` if missing or outside tenant scope.

---

## 5. Tenant Isolation and Authorization Controls
1. **Server-Side Identity Enforcement**: All dataset operations derive tenant scope from `current_user.org_id`.
2. **Cross-Tenant Privacy**:
   - Organization A cannot view, list, or access Organization B's evaluation datasets (`GET /api/simulation/eval-data/{name}` returns `404 Not Found`).
   - Scoping by `org_id` allows Organization A and Organization B to independently maintain datasets with the same name without collision.
3. **Role-Based Write Protection**:
   - Importing datasets requires administrative, security, or developer roles.
   - Read-only users (`VIEWER`) receive `403 Forbidden` if attempting to import datasets.
   - Unauthenticated requests receive `401 Unauthorized`.
4. **Duplicate Protection**: Duplicate imports within the same organization are rejected (`status="REJECTED"`), preventing silent or accidental overwrites.
5. **Atomic Transactions**: If any record or field insertion fails, `db.rollback()` executes, guaranteeing zero partial or orphaned datasets.

---

## 6. Verification and Test Results

### 1. Focused Dataset Persistence Tests (`backend/tests/test_evaluation_datasets_persistence.py`)
```bash
pytest backend/tests/test_evaluation_datasets_persistence.py -v
```
**Results: 11 passed in 5.82s**
- `test_01_successful_dataset_import`: PASSED
- `test_02_dataset_retrieval_by_name`: PASSED
- `test_03_listing_datasets`: PASSED
- `test_04_persistence_across_simulated_backend_restart`: PASSED
- `test_05_duplicate_dataset_handling`: PASSED
- `test_06_invalid_dataset_payload_rejection`: PASSED
- `test_07_transaction_rollback_on_import_failure`: PASSED
- `test_08_organization_isolation`: PASSED
- `test_09_unauthorized_import_and_retrieval`: PASSED
- `test_10_preservation_of_provenance_labels_and_action_sequences`: PASSED
- `test_11_simulation_integrity_and_isolation_regression`: PASSED

### 2. Full Regression & PACE Test Suite
```bash
pytest backend/tests/test_evaluation_datasets_persistence.py backend/tests/test_pace_simulation_lab.py backend/tests/test_predictive_action_control_engine.py backend/tests/test_phase4_product_integration.py backend/tests/test_runtime_authorization_suite.py -q
```
**Results: 70 passed in 14.19s**
- `test_evaluation_datasets_persistence.py`: 11 passed
- `test_pace_simulation_lab.py`: 10 passed
- `test_predictive_action_control_engine.py`: 20 passed
- `test_phase4_product_integration.py`: 8 passed
- `test_runtime_authorization_suite.py`: 21 passed

### 3. Frontend Type-Check & Build
- `npx tsc --noEmit` in `frontend/`: **Clean (0 errors, exit code 0)**
- `npm run build` in `frontend/`: **Clean (59/59 static pages generated, exit code 0)**

---

## 7. Evidence of Persistence Across Restart / New Session
Verified through automated test `test_04_persistence_across_simulated_backend_restart`:
1. A dataset was imported into the database in one session.
2. The in-memory runner was completely discarded, and a new `SimulationRunner` instance was constructed with a brand-new database session.
3. `fresh_runner.get_evaluation_dataset("alpha_procurement_eval_v1", db=db, org_id=org_a_id)` successfully loaded the dataset, all records, and metadata directly from the database.
4. `fresh_runner.list_evaluation_datasets(db=db, org_id=org_a_id)` correctly listed the dataset summary with matching record count and tags.

---

## 8. Known Limitations and Rollback Instructions

### Known Limitations
1. **Simulation Run Outcomes**: Individual simulation run execution traces (`SimulationRunner._runs`) remain in-memory by design as transient benchmark sessions.
2. **Payload Size Boundaries**: Maximum dataset record count is bounded at 500 records and sequence depth at 50 steps to prevent denial-of-service through oversized JSON payloads.

### Rollback Instructions
If rollback is required:
1. Revert `backend/models.py`, `backend/bootstrap.py`, `backend/engines/simulation_engine.py`, and `backend/routers/simulation.py` to their previous Git commit.
2. Database cleanup: In PostgreSQL or SQLite:
   ```sql
   DROP TABLE IF EXISTS evaluation_dataset_records CASCADE;
   DROP TABLE IF EXISTS evaluation_datasets CASCADE;
   ```
3. Existing tables (`agents`, `organizations`, `decisions`, `audit_logs`, etc.) are completely unmodified and unaffected.
