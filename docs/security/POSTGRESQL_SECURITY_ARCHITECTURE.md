# AGENTGUARD PostgreSQL Defense-in-Depth Security Architecture

## 1. Executive Summary & Security Objectives

AGENTGUARD enforces a zero-trust, multi-layered tenant isolation model. The primary isolation boundary is enforced at the **application layer** in the FastAPI backend routers and SQLAlchemy queries, while the secondary, defense-in-depth boundary is enforced at the **database engine layer** using PostgreSQL Row Level Security (RLS) and PostgREST role privilege hardening.

This dual-layer architecture guarantees that even in the catastrophic event of an application logic defect, an unvetted SQL query, or an insecure PostgREST direct endpoint exposure, database rows belonging to Tenant A remain cryptographically and logically inaccessible to Tenant B.

```
                           [ Incoming Request ]
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │  FastAPI Authentication Gate  │
                   │  - JWT Verification           │
                   │  - API Key Scopes Check       │
                   │  - Tenant Membership Binding  │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │  Layer 1: Application Defense │
                   │  - Router-level org_id filters│
                   │  - Fail-closed orphan checks  │
                   │  - Verified SUPER_ADMIN roles │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │  Database Connection Pool     │
                   │  - SET LOCAL app.curr_org_id  │
                   │  - Scoped to Transaction      │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │  Layer 2: Engine RLS Defense  │
                   │  - Direct org_id RLS policies │
                   │  - Parent-child subquery joins│
                   │  - Revoked PostgREST direct   │
                   └───────────────────────────────┘
```

---

## 2. Authentication vs Database Security Boundaries

| Responsibility | Layer | Component / Mechanism | Failure Mode |
|---|---|---|---|
| User Identity Verification | Application | Supabase Auth JWT / Password Hash | 401 Unauthorized |
| Organization Membership | Application | `current_user.org_id` / `entity.org_id` | 403 Forbidden |
| Role & Permission Check | Application | `require_admin`, `require_super_admin` | 403 Forbidden |
| Session Revocation | Application + DB | `models.Session.revoked` check | 401 Unauthorized |
| Direct Query Filtering | Application | `.filter(Model.org_id == org_id)` | 404 Not Found (Fail-closed) |
| Engine Row Isolation | Database | PostgreSQL RLS (`ENABLE ROW LEVEL SECURITY`) | 0 rows returned / 0 rows updated |
| Direct HTTP PostgREST API | Database | Role Privilege Revocation (`REVOKE ALL FROM anon`) | 403 Insufficient Privileges |

---

## 3. Verified PostgreSQL Role Attributes & PostgREST Architecture

Catalog introspection of the live production Supabase instance (`xjragvyzlailmtfwjfnm`) established the authoritative role topology:

| Role Name | Superuser (`rolsuper`) | Inherits (`rolinherit`) | Can Login (`rolcanlogin`) | Bypass RLS (`rolbypassrls`) | Application Purpose |
|---|---|---|---|---|---|
| `postgres` | `false` | `true` | `true` | `true` | Backend database pool user; table owner; Alembic migrations. |
| `service_role` | `false` | `true` | `false` | `true` | Supabase internal backend role; background workers. |
| `authenticated` | `false` | `true` | `false` | `false` | Web/API authenticated user role assumed by PostgREST with valid JWT. |
| `anon` | `false` | `true` | `false` | `false` | Unauthenticated public role used by Supabase client SDKs. |
| `authenticator` | `false` | `false` | `true` | `false` | PostgREST connection role; switches via `SET LOCAL ROLE` to `anon`, `authenticated`, or `service_role`. |

### Critical Behavioral Findings:
1. **`BYPASSRLS` Mechanics**:
   - Because `postgres` and `service_role` possess `rolbypassrls = true`, queries executed directly under these roles bypass standard RLS policies automatically.
   - However, if `FORCE ROW LEVEL SECURITY` is applied to a table, PostgreSQL forces policies even on table owners unless explicitly bypassed by a `service_role` policy.
2. **Current Privilege Exposure**:
   - Live database auditing revealed that while `anon` and `authenticated` have `SELECT`, `INSERT`, `UPDATE`, and `DELETE` denied, both roles currently hold **`TRUNCATE`**, **`REFERENCES`**, and **`TRIGGER`** on all 50 public tables.
   - Full privilege revocation (`REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;`) is strictly required to close this exposure.

---

## 4. Tenant Context & GUC Security Analysis

### The GUC Spoofing Limitation
The preliminary RLS migration relied on:
```sql
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS uuid LANGUAGE sql STABLE AS $$
    SELECT nullif(current_setting('app.current_org_id', true), '')::uuid;
$$;

CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT coalesce(current_setting('app.is_super_admin', true) = 'true', false);
$$;
```

#### Identified Security Limitations:
1. **User Settable GUCs**: In PostgreSQL, custom GUC variables (in any prefix, e.g. `app.*`) are not restricted by default. Any session with SQL query execution privileges can execute:
   ```sql
   SET app.is_super_admin = 'true';
   SET app.current_org_id = 'victim-tenant-uuid';
   ```
   This would instantly grant cross-tenant read/write access.
2. **PostgREST Disconnect**: PostgREST sets `request.jwt.claims` and `auth.uid()`, but does **not** execute `SET app.current_org_id`. As a result, direct PostgREST calls evaluate `current_org_id()` to `NULL`, returning 0 rows for legitimate users.

### The Hardened Dual-Resolution Architecture
To resolve both GUC spoofing and PostgREST compatibility:
```sql
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    -- 1. If PostgREST request, resolve tenant from verified JWT claim or user profile
    SELECT COALESCE(
        -- PostgREST app_metadata or user_metadata claim
        nullif(current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'org_id', '')::uuid,
        -- Fallback to authoritative database profile lookup via auth.uid()
        (SELECT org_id FROM public.users WHERE auth_user_id = auth.uid() OR id = auth.uid() LIMIT 1),
        -- Backend transaction-scoped local setting (SET LOCAL)
        nullif(current_setting('app.current_org_id', true), '')::uuid
    );
$$;

CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    -- Check verified JWT claim or authoritative database profile role
    SELECT COALESCE(
        (current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'role') = 'SUPER_ADMIN',
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE (auth_user_id = auth.uid() OR id = auth.uid()) 
              AND role = 'SUPER_ADMIN' 
              AND status = 'ACTIVE'
        ),
        (current_setting('app.is_super_admin', true) = 'true' AND current_user IN ('postgres', 'service_role')),
        false
    );
$$;
```

---

## 5. Connection Pooling & Transaction Scoping

### The Connection-Pool Leaking Risk
In a production deployment using connection pooling (Supavisor / SQLAlchemy `QueuePool`), connections are reused across multiple requests.
If an application executes session-level `SET app.current_org_id = '...'`, the setting persists when the connection returns to the pool, bleeding Tenant A's identity into Tenant B's request.

### The Strict Remediation: `SET LOCAL` Inside Explicit Transactions
All backend tenant context configuration must use `SET LOCAL` inside an explicit transaction boundary:
```sql
BEGIN;
SET LOCAL app.current_org_id = '00000000-0000-0000-0000-000000000001';
SET LOCAL app.is_super_admin = 'false';

SELECT * FROM agents; -- Evaluated strictly for Org 1

COMMIT;
-- Pool connection is now completely sanitized and has no lingering context.
```

In SQLAlchemy:
```python
@event.listens_for(Session, "after_begin")
def set_tenant_context(session, transaction, connection):
    org_id = getattr(session, "tenant_org_id", None)
    is_super = getattr(session, "is_super_admin", False)
    if org_id:
        connection.execute(text(f"SET LOCAL app.current_org_id = '{org_id}'"))
    if is_super:
        connection.execute(text("SET LOCAL app.is_super_admin = 'true'"))
```

---

## 6. Celery Worker & Asynchronous Task Execution

1. **Tenant-Scoped Workers**:
   - Webhook workers and report workers receive `org_id` in the task payload.
   - Upon task inception, the worker opens an explicit database transaction and executes `SET LOCAL app.current_org_id = :org_id`.
2. **System-Level Scheduled Jobs (Beat)**:
   - System jobs (expired token purging, daily metrics aggregation) operate across organizations.
   - Workers connect under `postgres` or `service_role` credentials which possess `BYPASSRLS`.

---

## 7. Failure Modes & Fail-Closed Invariants

1. **Unset Tenant Context**:
   - `public.current_org_id()` returns `NULL`.
   - Condition `org_id = public.current_org_id()` evaluates to `org_id = NULL`, which evaluates to `UNKNOWN` (falsy in SQL boolean logic).
   - Zero rows returned / zero rows updated. **Fails closed.**
2. **Invalid UUID Format**:
   - `nullif(..., '')::uuid` catches empty strings and returns `NULL` rather than throwing a cast exception.
3. **Database Migration Safety**:
   - Alembic migrations execute under the `postgres` role.
   - Table modifications (`ALTER TABLE ... ADD COLUMN`) succeed without RLS interference because `postgres` is the table owner and has `rolbypassrls = true`.
