# AGENTGUARD — DATABASE MIGRATION & RECONCILIATION RUNBOOK

**Document Version:** 2.1.0 (Alembic Baseline Reconciliation & 12-Point Schema Parity)  
**Classification:** Enterprise Control Plane Database Operations  

---

## 1. Dual-Tier Database Architecture & Ownership Model

To prevent schema divergence and split-brain migrations between Alembic and Supabase, AGENTGUARD enforces a strict separation of database ownership:

| Layer / Responsibility | Governing System | Source of Truth | Scope |
| :--- | :--- | :--- | :--- |
| **Application Schema** | **Alembic** | `backend/alembic/versions/` | All 49 baseline application tables, plus forward extension tables (e.g. `otp_challenges`), columns, data types, nullability, primary keys, foreign keys, unique constraints, and indexes. |
| **Infrastructure & Security** | **Supabase Migrations** | `supabase/migrations/` | PostgreSQL extensions (`uuid-ossp`, `pgcrypto`), Row-Level Security (RLS) policies (`ENABLE ROW LEVEL SECURITY`, `CREATE POLICY`), database roles, and connection grants. |
| **Canonical Seed Data** | **Application Bootstrap** | `backend/bootstrap.py` | Idempotent reference data seeding (canonical subscription plans `FREE`, `STARTER`, `PROFESSIONAL`, `ENTERPRISE`). |

### Core Architectural Invariants
1. **Zero DDL Duplication:** Application tables and columns must **never** be defined or altered via raw SQL in Supabase migrations. They are exclusively authored in SQLAlchemy models and generated via Alembic.
2. **`AUTO_BOOTSTRAP_DB=false` in Production:** Startup DDL creation (`create_all()`) is strictly prohibited in production and staging environments to protect database integrity.
3. **Explicit Operator Authorization:** Neither `main.py`, `bootstrap.py`, nor Celery workers perform automatic baseline adoption or schema migrations. Migrations must be separately authorized and executed by an operator.

---

## 2. Alembic Migration Hierarchy

```text
(Base) 
  │
  ▼
[ 0001_initial_canonical_schema ]  <-- 49 baseline application tables (canonical control plane)
  │
  ▼
[ 0002_add_otp_challenges ]        <-- otp_challenges table (HMAC storage, 120s cooldown, 6 indexes)
```

* **Revision `0001_initial_canonical_schema`:** Baseline canonical schema capturing all 49 core platform tables (`organizations`, `users`, `sessions`, `agents`, `decisions`, etc.).
* **Revision `0002_add_otp_challenges`:** Creates the `otp_challenges` table with HMAC hash representation, 120-second resend cooldown boundary, 10-minute expiry, 5-attempt brute-force lockout, and 6 performance indexes.

---

## 3. Preflight Schema Audit & Status Classifications

The reconciliation tool provides a read-only, non-mutating preflight audit:

```bash
python backend/scripts/reconcile_alembic_baseline.py --preflight
```

### Preflight Status Taxonomy
* **`EMPTY`**: Zero tables found in the database. Safe for greenfield `alembic upgrade head`.
* **`MATCHING_UNSTAMPED_BASELINE`**: Exactly 49 baseline tables match the canonical manifest 1:1; `alembic_version` is absent; `otp_challenges` is absent. **Only in this state is adoption permitted.**
* **`ALREADY_ADOPTED`**: `alembic_version` already contains `0001_initial_canonical_schema` or `0002_add_otp_challenges`.
* **`PARTIALLY_MIGRATED`**: Incomplete set of baseline tables found (< 49). Adoption is strictly blocked.
* **`SCHEMA_MISMATCH`**: Tables exist but column, type, nullability, PK, or FK differences are detected. Adoption is strictly blocked.
* **`CONFLICTING_REVISION`**: `alembic_version` exists but points to an unrecognized or conflicting revision. Adoption is strictly blocked.

### 12-Point Schema Parity Audit Matrix
The tool evaluates 12 categories, reporting `[MATCH]`, `[MISMATCH]`, `[NOT CHECKED]`, or `[NOT APPLICABLE]`:
1. **Column Data Types:** Invariant type categories (String, Integer, Float, DateTime, JSON, GUID).
2. **Nullability:** Strict validation of required `NOT NULL` columns.
3. **Server Defaults:** Defaults inspection.
4. **Identity & Generated Columns:** Application-level UUID generation (`NOT APPLICABLE`).
5. **Primary Keys:** Constrained columns and single/composite PK definitions.
6. **Foreign Keys:** References, constrained local columns, and target tables.
7. **Unique Constraints:** Table-level and column-level unique constraints.
8. **Check Constraints:** Table check constraints.
9. **Index Definitions:** Names, target columns, and uniqueness.
10. **Sequences & Ownership:** Sequence bindings (`MATCH`).
11. **PostgreSQL Extensions:** Verified `uuid-ossp` and `pgcrypto` installed (`MATCH`).
12. **RLS Policies & Grants:** Verified Supabase RLS security layer (`MATCH`).

---

## 4. Existing Database Baseline Adoption (Reconciliation)

When adopting an existing database whose baseline was provisioned prior to Alembic tracking:

> [!CAUTION]
> Never run `alembic upgrade head` blindly on an unstamped existing database! It will attempt to recreate existing tables and fail with `relation already exists`.
> Production adoption and migration require separate explicit authorization.

### Step 1: Pre-Migration Backup Snapshot
Always take an authoritative database dump prior to adoption:
```bash
pg_dump -h <HOST> -p 5432 -U <USER> -d <DBNAME> -F c -b -v -f /backups/pre_reconciliation_$(date +%Y%m%d_%H%M%S).dump
```

### Step 2: Run Read-Only Preflight
```bash
python backend/scripts/reconcile_alembic_baseline.py --preflight
```
Confirm `Audit Status: MATCHING_UNSTAMPED_BASELINE` and `Eligible for Adoption: True`.

### Step 3: Execute Authorized Adoption
```bash
python backend/scripts/reconcile_alembic_baseline.py --adopt --confirm
```
*Stamps `0001_initial_canonical_schema` transactionally without modifying application data.*

### Step 4: Apply Migration 0002
```bash
alembic upgrade head
```

### Step 5: Verify Post-Migration Revision & Schema
```bash
alembic current
python -c "
from database import engine
from sqlalchemy import inspect
insp = inspect(engine)
assert 'otp_challenges' in insp.get_table_names(), 'otp_challenges missing!'
indexes = {ix['name'] for ix in insp.get_indexes('otp_challenges')}
assert len(indexes) == 6, f'Expected 6 indexes, found {len(indexes)}'
print('SUCCESS: otp_challenges created with all 6 indexes!')
"
```

---

## 5. Greenfield (Fresh) Database Installation

For a brand new empty database:
```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
alembic upgrade head
```
Executes `0001_initial_canonical_schema` followed by `0002_add_otp_challenges` cleanly.

---

## 6. Rollback & Disaster Recovery Procedures

### A. Rolling Back Migration 0002
If an issue occurs with `otp_challenges`, downgrade safely to revision 0001:
```bash
alembic downgrade 0001_initial_canonical_schema
```
* **Effect:** Drops table `otp_challenges` and its 6 indexes.
* **Safety:** Does **not** touch or drop any of the 49 baseline application tables.

### B. Recovery from an Interrupted Migration
1. Inspect current recorded revision: `alembic current`
2. Run preflight: `python backend/scripts/reconcile_alembic_baseline.py --preflight`
3. Drop any orphaned index attempts if necessary, and re-run `alembic upgrade head`.

---

## 7. Isolated Staging Database Validation Workflow

When Docker Desktop or an authorized staging PostgreSQL instance is available:
```bash
# 1. Start isolated staging containers
docker-compose -f docker-compose.staging.yml up -d staging-postgres staging-redis

# 2. Configure environment
export DATABASE_URL="postgresql://agentguard_stage:stage_test_pass_only@127.0.0.1:5433/agentguard_staging"

# 3. Test greenfield migration
alembic upgrade head

# 4. Run test suites
pytest backend/tests/test_alembic_baseline_reconciliation.py -v
pytest backend/tests/test_authentication_and_otp_flows.py -v
pytest backend/tests/test_registration_consistency_scenarios.py -v
pytest backend/tests/test_otp_cleanup_and_reconciliation.py -v
```
