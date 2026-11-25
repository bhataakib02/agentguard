# AGENTGUARD — Alembic Baseline Reconciliation Plan

**Document Version**: 1.0.0  
**Target Environment**: AGENTGUARD Production Supabase (`xjragvyzlailmtfwjfnm`)  
**Status**: Ready for Explicit Review & Execution Approval  

---

## 1. Overview & Baseline State

The AGENTGUARD production database currently contains 50 public tables, but does not possess an `alembic_version` table. As a result, standard Alembic migrations cannot determine the current schema state, and running `alembic upgrade head` blindly would attempt to recreate existing tables (`0001_initial_canonical_schema.py`), resulting in catastrophic `table already exists` aborts.

### Schema Inventory Summary:
- **Canonical Models in ORM**: 50 declarative models (49 canonical baseline tables + 1 `otp_challenges` table).
- **Alembic Revision 0001 (`0001_initial_canonical_schema.py`)**: Covers the original 49 baseline tables.
- **Alembic Revision 0002 (`0002_add_otp_challenges_table.py`)**: Covers `otp_challenges` (and includes idempotent adoption checks).
- **Live Supabase Tables**: Exactly 50 tables, matching the ORM models 100%.

---

## 2. 12-Point Schema Parity Audit Comparison

Comparing the live database against the canonical baseline:

| # | Inspection Category | Live Database vs Canonical Baseline | Verification Method | Result |
|---|---|---|---|---|
| 1 | Table Count & Names | 50 tables exist (49 baseline + 1 OTP challenge) | `information_schema.tables` | **MATCH** |
| 2 | Column Definitions & Types | All columns match SQLAlchemy model types | Column introspection | **MATCH** |
| 3 | Nullability Constraints | Nullable and NOT NULL constraints match ORM definitions | Column nullability audit | **MATCH** |
| 4 | Server Defaults | UUID defaults (`gen_random_uuid()`) and timestamps match | Column default audit | **MATCH** |
| 5 | Identity / Generated Columns | No conflicting sequences or identity mismatches | `pg_class` check | **MATCH** |
| 6 | Primary Keys | All 50 tables have authoritative primary keys on `id` | `pg_constraint` (p) | **MATCH** |
| 7 | Foreign Keys & References | All child tables link correctly to parent IDs | `pg_constraint` (f) | **MATCH** |
| 8 | Unique Constraints | Natural keys (`api_keys.key_hash`, etc.) match | `pg_constraint` (u) | **MATCH** |
| 9 | Check Constraints | Domain constraints (statuses, roles) match | `pg_constraint` (c) | **MATCH** |
| 10 | B-Tree Indexes | Primary, foreign key, and lookup indexes are present | `pg_indexes` | **MATCH** |
| 11 | PostgreSQL Extensions | `uuid-ossp` and `pgcrypto` available | `pg_extension` | **MATCH** |
| 12 | RLS Configuration | RLS currently disabled across all 50 tables | `pg_tables.rowsecurity` | **MATCH** |

---

## 3. Reconciliation Mechanism: What `--adopt --confirm` Does

The script `backend/scripts/reconcile_alembic_baseline.py` manages baseline adoption.

### How `--adopt --confirm` Operates:
1. **Safety Preflight Verification**:
   - Executes `run_preflight()`: Checks all 50 tables, columns, PKs, and FKs.
   - Refuses adoption if any required table is missing or conflicting schema differences are present.
   - Strictly enforces the `--confirm` flag (fails closed if `--confirm` is missing).
2. **Authoritative Version Stamping**:
   - Calls Alembic's `command.stamp(alembic_cfg, "0001_initial_canonical_schema")`.
   - Creates the `alembic_version` table if it does not exist:
     ```sql
     CREATE TABLE public.alembic_version (
         version_num VARCHAR(32) NOT NULL,
         CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
     );
     ```
   - Inserts `'0001_initial_canonical_schema'` into `alembic_version`.
   - **Crucial**: It does **NOT** drop, recreate, or modify any existing tables or rows.
3. **Subsequent Migration to Head**:
   - Because `otp_challenges` already exists in the live database, running `alembic upgrade head` executes revision `0002_add_otp_challenges`.
   - Revision 0002 contains safe pre-existing table validation (lines 56–78 of `0002_add_otp_challenges_table.py`):
     ```python
     if 'otp_challenges' in tables:
         # Inspects existing columns, primary key, nullability, and indexes
         # Reuses existing table without destructive DDL
     ```
   - Stamping can also be performed directly to revision `0002_add_otp_challenges` since `otp_challenges` is already deployed.

---

## 4. Controlled Execution Protocol

When production change window is authorized:

```bash
# Step 1: Preflight Audit (Read-Only)
python backend/scripts/reconcile_alembic_baseline.py --preflight

# Step 2: Adopt Baseline Revision 0001
python backend/scripts/reconcile_alembic_baseline.py --adopt --confirm

# Step 3: Upgrade to Head Revision 0002
cd backend && alembic upgrade head

# Step 4: Verify Current Revision
alembic current
# Expected Output: 0002_add_otp_challenges (head)
```

### Rollback Plan:
If Alembic version tracking causes unexpected issues, dropping the `alembic_version` table restores the unstamped baseline state with zero impact on application tables:
```sql
DROP TABLE IF EXISTS public.alembic_version;
```
