# AGENTGUARD Security & IAM Documentation

Welcome to the AGENTGUARD Security & Governance documentation directory. This folder provides detailed specifications of the AGENTGUARD zero-trust security model, access control architecture, and multi-tenant isolation guarantees.

---

## 1. Available Documentation

- [Enterprise IAM & Permission Matrix](IAM_ROLE_MATRIX.md): Comprehensive documentation of the canonical 5-role organizational IAM architecture, granular permissions, role hierarchy levels, and platform operator (`SUPER_ADMIN`) isolation.
- Root [SECURITY.md](../../SECURITY.md): Responsible disclosure policy, supported versions, and vulnerability reporting procedures.

---

## 2. Core Security Guarantees

1. **Non-Bypassable Runtime Interception:** Autonomous agents cannot interact directly with downstream systems without verified clearance from the Predictive Action Control Engine (PACE).
2. **Tenant Organization Isolation:** User identities, policies, audit events, and agent credentials are partitioned by unique `org_id` foreign keys with database-level constraints.
3. **Cryptographic Tamper-Evidence:** All administrative and agent execution events are anchored in an append-only audit trail bound by SHA-256 hash chains (`record_hash = SHA256(previous_hash + payload)`).
4. **Zero-Trust Identity Enforcement:** Server-side authorization dependencies validate authentic database sessions; client-supplied role headers (`X-Role`) are never trusted.
