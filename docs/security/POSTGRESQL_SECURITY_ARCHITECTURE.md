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
| Direct HTTP PostgREST API | Database | Role Privilege Revocation (`REVOKE FROM anon`) | 403 Insufficient Privileges |

---

## 3. PostgREST & Supabase Role Architecture

Supabase exposes PostgreSQL over HTTP using PostgREST. Understanding the interaction between database roles is critical:

1. **`anon` (Anonymous Web Role)**:
   - Used when requests carry no Authorization header or use the public `anon` publishable key.
   - **Hardening Policy**: Must have `REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;`. The `anon` role is barred from selecting, inserting, updating, or deleting any internal AGENTGUARD data.
2. **`authenticated` (Signed-in User Role)**:
   - Assumed by PostgREST when a valid user JWT is provided.
   - **Hardening Policy**: Granted CRUD on public schema, but strictly subject to Row Level Security (`ENABLE ROW LEVEL SECURITY`). Every row operation evaluates against `public.current_org_id()`.
3. **`service_role` (Backend / Admin Role)**:
   - Used by the FastAPI backend application and secure Celery asynchronous workers.
   - Bypasses RLS policies via explicit `service_role_all` bypass policies (`USING (true) WITH CHECK (true)`).
4. **`postgres` / Superuser**:
   - Administrative role used exclusively for running Alembic schema migrations and maintenance.

---

## 4. Connection Pooling & Tenant Context Hygiene

### The Connection-Pool Leaking Risk
In a production deployment using connection pooling (such as SQLAlchemy `QueuePool`, PgBouncer in transaction pooling mode, or Supavisor), connections are reused across multiple HTTP requests.
If an application executes:
```sql
-- DANGEROUS: Session-level setting persists across pool check-in!
SET app.current_org_id = 'org-uuid-123';
```
That connection, when returned to the pool and checked out by a subsequent request for Tenant B, will retain Tenant A's context if not explicitly cleared.

### The Strict Remediation: Transaction Scoping with `SET LOCAL`
All tenant context settings in AGENTGUARD must use `SET LOCAL` inside an explicit transaction boundary:
```sql
BEGIN;
-- Safe: setting automatically disappears on COMMIT or ROLLBACK
SET LOCAL app.current_org_id = '00000000-0000-0000-0000-000000000001';
SET LOCAL app.is_super_admin = 'false';

SELECT * FROM agents; -- Evaluated strictly for Org 1

COMMIT;
-- Pool connection is now completely sanitized and has no lingering context.
```

In SQLAlchemy, this is integrated via session lifecycle events or connection checkout listeners:
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

## 5. Celery Worker, Beat & System Job Execution

Celery workers process asynchronous jobs (such as SIEM batch delivery, scheduled report generation, webhook retries, and approval escalation):

1. **Tenant-Scoped Workers**:
   - Webhook workers and report workers receive `org_id` in the task payload.
   - Upon task inception, the worker opens a database transaction and executes `SET LOCAL app.current_org_id = :org_id`.
2. **System-Level Scheduled Jobs (Beat)**:
   - System jobs (e.g. database vacuum, global license limit reconciliation, expired token purging) operate across organizations.
   - System workers authenticate via `service_role` credentials or set `SET LOCAL app.is_super_admin = 'true'`.

---

## 6. Failure Modes & Fail-Closed Principles

1. **Unset Tenant Context (`current_setting` returns NULL)**:
   - `public.current_org_id()` returns `NULL`.
   - Condition `org_id = public.current_org_id()` evaluates to `org_id = NULL`, which is `UNKNOWN` (falsy in SQL boolean logic).
   - Zero rows are returned. **Fails closed.**
2. **Invalid UUID Format**:
   - `nullif(current_setting('app.current_org_id', true), '')::uuid` catches empty strings and returns `NULL` rather than throwing a cast exception.
3. **Database Migration Lockout Prevention**:
   - Alembic migrations execute under the `postgres` / superuser role.
   - Table modifications (`ALTER TABLE ... ADD COLUMN`) are unrestricted because table owners and superusers bypass RLS unless `FORCE ROW LEVEL SECURITY` is applied without owner bypass policies.
