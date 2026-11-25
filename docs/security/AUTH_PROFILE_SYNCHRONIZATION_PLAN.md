# AGENTGUARD — Authentication Profile Synchronization Plan

**Document Version**: 1.0.0  
**Context**: Supabase Auth (`auth.users`) vs AGENTGUARD Public Profile (`public.users`)  
**Status**: Architecture & Safe Remediation Design  

---

## 1. Investigation Findings: Auth Users vs Public Users

A read-only catalog query against the live database (`xjragvyzlailmtfwjfnm`) revealed:
- `auth.users` count: **1**
- `public.users` count: **1**
- Email match: **TRUE** (both tables contain the same Super Admin email)
- ID match (`auth.users.id = public.users.id`): **FALSE** (`public.users.id` was generated independently via `uuid.uuid4()`)
- `public.users.auth_user_id`: **Populated** with `auth.users.id`
- Database Triggers: **0** (No triggers exist on `auth.users` or `public.users` to synchronize profiles)

### Historical Context on the Reported "45 auth.users vs 4 public.users":
In earlier development and testing phases, 45 test users were provisioned directly via Supabase Auth without public profiles, while 4 organizations were seeded. Subsequently, `supabase/clean_production_data.sql` was executed as part of maintenance safeguards, which safely purged unattached demo accounts (`DELETE FROM auth.users WHERE id <> sa_auth_id;`), leaving exactly 1 preserved Super Admin user in both tables.

---

## 2. Application-Layer Identity Resolution Flow

Inspection of `backend/core/deps.py` (`get_current_user`, lines 265–290) demonstrates how AGENTGUARD handles authentication without requiring synchronous database triggers:

```python
# 1. Cryptographically verify Supabase JWT
verified = verify_supabase_token(token)
user_id, email = verified  # user_id is auth.users.id

# 2. Authoritative Database Profile Resolution
user = db.query(models.User).filter(
    (models.User.id == user_id) | (models.User.auth_user_id == user_id)
).first()

# 3. Fallback to Email Resolution & Lazy auth_user_id Binding
if not user and email:
    user = db.query(models.User).filter(
        (models.User.email == email) | (func.lower(models.User.email) == email.lower().strip())
    ).first()
    if user and user_id and not user.auth_user_id:
        user.auth_user_id = user_id
        db.commit()

# 4. Fail-Closed Boundary: If no public profile exists, reject with 401
if not user:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User identity verified via Supabase Auth, but public profile does not exist. Complete registration or contact administrator."
    )
```

### Key Architectural Behaviors:
1. **Self-Healing Linking**: When a user registers or logs in, if `public.users.auth_user_id` is null, the backend binds `auth_user_id = auth.users.id` automatically on the first authenticated request.
2. **Fail-Closed Isolation**: A user created directly in Supabase Auth (e.g. via Supabase dashboard or social login) who lacks a `public.users` record cannot access AGENTGUARD API endpoints. The system returns HTTP 401.
3. **Decoupled User Model**: `public.users` has its own surrogate UUID (`id`), organization reference (`org_id`), role (`role`), and department. It does not force `public.users.id == auth.users.id`, providing schema portability across auth providers.

---

## 3. Safe Synchronization Strategy (Zero-Downtime, Non-Destructive)

If external Supabase Auth users exist that need public profiles:

### Why Database Triggers Are NOT Recommended:
- Direct triggers on `auth.users` (`AFTER INSERT ON auth.users`) violate domain separation between Supabase Auth and AGENTGUARD multi-tenancy.
- An `auth.users` row contains no `org_id`, `role`, or `plan_tier`. Creating a dummy `public.users` record without an organization breaks foreign keys and defaults to insecure tenantless states.
- If the trigger fails (e.g., duplicate email or missing fields), user sign-up in Supabase Auth is blocked entirely.

### Recommended Controlled Synchronization Protocol:
1. **Application Registration Endpoint (`POST /api/auth/register-verified`)**:
   - The user completes OTP verification or Supabase Auth registration.
   - The backend creates the `Organization`, creates the `User` with `auth_user_id = auth.users.id` and `org_id = org.id`, and assigns the safe initial role (`ADMIN` of their new org or `USER` if invited).
2. **Backfill Script for Orphaned Auth Users**:
   If unattached users exist, run a dry-run reconciliation script:
   ```python
   # Read-only inspection of unlinked auth accounts
   unlinked = db.execute(text("""
       SELECT a.id, a.email, a.created_at
       FROM auth.users a
       LEFT JOIN public.users u ON u.auth_user_id::text = a.id::text OR lower(u.email) = lower(a.email)
       WHERE u.id IS NULL;
   """)).fetchall()
   ```
3. **No Automatic Bulk Backfill**:
   Never generate synthetic public profiles without explicit tenant assignment and organization binding.
