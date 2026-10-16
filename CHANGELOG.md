# Changelog

All notable changes to the **AGENTGUARD** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Standardized documentation structure under `docs/` with comprehensive guides, runbooks, specifications, and architecture references.
- Official root `LICENSE` file under the Apache License 2.0.
- Repository-wide `SECURITY.md` detailing vulnerability disclosure policies and reporting procedures.
- `CONTRIBUTING.md` establishing code conventions, verification standards, and pull request procedures.
- Backend regression test `test_06_platform_security_authorization_and_isolation` validating zero-trust role authorization on `/api/platform/security`.

### Changed
- Reconciled and documented backend regression test suite selections (157 selective vs 173 comprehensive).
- Corrected hierarchical IAM level mapping in documentation (Platform `SUPER_ADMIN` at Level 9, Organizational `ADMIN` at Level 8).
- Migrated design specifications from legacy `documents/` directory into unified `docs/specifications/` directory.

### Security
- Verified zero-trust server-side authorization on all platform administration endpoints.
- Confirmed purge of transient test fixtures and verified no secrets are tracked in source control.

---

## [1.0.0] - 2026-10-16

### Added
- **Predictive Action Control Engine (PACE):** Real-time heuristic and semantic evaluation gate enforcing `ALLOW`, `REVIEW`, and `REFUSE` outcomes on autonomous tool calls.
- **Enterprise IAM & Five-Role Architecture:** Canonical support for `ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, and `AGENT` with fine-grained permission matrices.
- **Global Platform Operator Model:** Isolated `SUPER_ADMIN` privilege tier for cross-tenant health and licensing without tenant boundary compromise.
- **Cryptographic Audit Log:** SHA-256 tamper-evident provenance hash-chaining across all agent actions and administrative events.
- **Persistent Evaluation Datasets:** Support for synthetic benchmarks and evaluation datasets with versioning, metrics, and risk scoring.
- **Python SDK (`agentguard`):** LangChain and CrewAI integration middleware, synchronous/asynchronous client interfaces, and automatic token management.
- **TypeScript SDK (`@agentguard/sdk`):** Native Node.js/TypeScript client with full type declarations and PACE evaluation wrappers.
- **Enterprise Web Dashboard:** 59 Next.js pages covering security monitoring, agent oversight, policy management, compliance reporting, and platform controls.
- **Deployment Assets:** Production Dockerfile, docker-compose configuration for Redis/Celery workers, and deployment manifests for Render and Vercel.
