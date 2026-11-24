# AGENTGUARD — DATABASE MIGRATION & RECONCILIATION RUNBOOK

**Document Version:** 2.0.0 (Alembic Baseline Reconciliation & Migration Ownership)  
**Classification:** Enterprise Control Plane Database Operations  

---

## 1. Database Migration Ownership Model

To prevent schema conflicts and split-brain migrations between Alembic and Supabase, AGENTGUARD enforces a strict separation of database concerns:

| Domain / Responsibility | Governing System | Location | Description |
| :--- | :--- | :--- | :--- |
| **Application Tables & Schema** | **Alembic** | `backend/alembic/versions/` | All application tables, columns, data types, primary keys, foreign keys, unique constraints, and performance indexes. |
| **Extensions, RLS & DB Roles** | **Supabase Migrations** | `supabase/migrations/` | PostgreSQL extensions (`uuid-ossp`, `pgcrypto`), Row-Level Security policies (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`), role grants, and security barriers. |
| **Canonical Seed Data** | **Application Bootstrap** | `backend/bootstrap.py` | Idempotent reference data seeding (such as canonical subscription plans `FREE`, `STARTER`, `PROFESSIONAL`, `ENTERPRISE`). |

### Rules for Schema Changes
1. **Never duplicate table DDL in both systems.** Application tables and columns must **only** be declared in SQLAlchemy models and managed via Alembic revision scripts.
2. **Never edit existing migration files** once deployed. Always generate a forward migration (`alembic revision -m "..."`).
3. **`AUTO_BOOTSTRAP_DB=false` in production.** Production databases must strictly be migrated through version-controlled Alembic migration executions. Startup DDL generation is prohibited.

---

## 2. Alembic Migration Hierarchy

```text
(Base) 
  │
  ▼
[ 0001_initial_canonical_schema ]  <-- Captures 49 baseline canonical application tables
  │
  ▼
[ 0002_add_otp_challenges ]        <-- Adds otp_challenges table and 6 performance indexes
```

* **Revision `0001_initial_canonical_schema`:** Baseline canonical schema covering all 49 core platform tables (organizations, users, sessions, agents, decisions, etc.).
* **Revision `0002_add_otp_challenges`:** Creates the `otp_challenges` table with HMAC hash storage, attempts tracking, expiry bounds, and 6 performance indexes.

---

## 3. Fresh (Greenfield) Database Provisioning

For a brand new, completely empty PostgreSQL database:

```bash
# 1. Ensure DATABASE_URL is configured
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# 2. Run Alembic upgrade head
alembic upgrade head
```

This sequentially executes:
1. `0001_initial_canonical_schema`: Creates extensions and all 49 baseline tables.
2. `0002_add_otp_challenges`: Creates `otp_challenges` and its indexes.
3. Sets `alembic_version` to `0002_add_otp_challenges`.

---

## 4. Existing Database Baseline Adoption (Reconciliation)

When connecting Alembic to an existing database whose baseline tables were provisioned prior to Alembic tracking (e.g. initial Supabase SQL schemas):

> [!CAUTION]
> Never run `alembic upgrade head` blindly on an unstamped existing database! It will attempt to recreate existing tables and fail with `relation already exists`.
> Never run `alembic stamp` without executing the automated preflight reconciliation audit.

### Step 1: Pre-Migration Backup
Always capture an authoritative snapshot prior to migration activities:
```bash
pg_dump -h <HOST> -p 5432 -U <USER> -d <DBNAME> -F c -b -v -f /backups/pre_reconciliation_$(date +%Y%m%d_%H%M%S).dump
```

### Step 2: Execute Read-Only Preflight Audit
Run the baseline reconciler in preflight mode:
```bash
python backend/scripts/reconcile_alembic_baseline.py --preflight
```

**Expected Preflight Output:**
* `Audit Status`: `MATCHING_UNSTAMPED_BASELINE`
* `Total Tables in DB`: `49`
* `Columns Audited`: `528`
* `Missing Baseline Tabs`: `[]`
* `Column Diffs`: `0`
* `Eligible for Adoption`: `True`

If any diffs, missing tables, or conflicting revisions are reported, **STOP**. Resolve the discrepancies before proceeding.

### Step 3: Authorized Baseline Adoption
Only after preflight reports `Eligible for Adoption: True`, execute the baseline adoption:
```bash
python backend/scripts/reconcile_alembic_baseline.py --adopt --confirm
```

This safely stamps `alembic_version` with `0001_initial_canonical_schema` without mutating or dropping any application data.

### Step 4: Apply Pending Migration 0002
Now that the baseline is authoritatively adopted, apply migration 0002:
```bash
alembic upgrade head
```

### Step 5: Post-Migration Verification
Verify that `otp_challenges` exists and `alembic_version` is at head:
```bash
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

## 5. Rollback & Disaster Recovery Procedures

### A. Rolling Back Migration 0002
If an issue occurs with `otp_challenges`, downgrade safely to revision 0001:
```bash
alembic downgrade 0001_initial_canonical_schema
```
* **Effect:** Drops the `otp_challenges` table and its 6 indexes.
* **Safety:** Does NOT drop or alter any of the 49 baseline application tables.

### B. Recovery from an Interrupted Migration
If a migration is interrupted (e.g., process termination or network disconnect):
1. Inspect the current revision in `alembic_version`:
   ```bash
   alembic current
   ```
2. Inspect the database with the preflight tool:
   ```bash
   python backend/scripts/reconcile_alembic_baseline.py --preflight
   ```
3. If partial objects exist, resolve the lock or drop uncommitted partial indexes, and re-run:
   ```bash
   alembic upgrade head
   ```

---

## 6. Isolated Staging Database Validation Workflow

When Docker Desktop or a staging PostgreSQL instance is available:
```bash
# 1. Start staging container
docker-compose -f docker-compose.staging.yml up -d staging-postgres

# 2. Point to staging database
export DATABASE_URL="postgresql://agentguard_stage:stage_test_pass_only@127.0.0.1:5433/agentguard_staging"

# 3. Validate greenfield upgrade chain
alembic upgrade head

# 4. Run test suite against staging database
pytest backend/tests/test_alembic_baseline_reconciliation.py -v
pytest backend/tests/test_authentication_and_otp_flows.py -v
pytest backend/tests/test_otp_cleanup_and_reconciliation.py -v
```
