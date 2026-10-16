# AGENTGUARD Master Documentation Index

Welcome to the central documentation index for **AGENTGUARD — Runtime Control Plane for Autonomous AI**.

This index provides a structured directory to all architecture models, technical guides, runbooks, specifications, and audit reports across the repository.

---

## 1. Getting Started & Guides

- [Local Setup Guide](guides/LOCAL_SETUP.md): Step-by-step local workstation installation, virtual environments, database initialization, and server startup.
- [Configuration Reference](guides/CONFIGURATION.md): Comprehensive reference for all backend and frontend environment variables, security keys, and CORS settings.
- [API Reference Guide](guides/API_GUIDE.md): Complete REST & WebSocket API specification covering authentication, agent registration, PACE evaluation, and telemetry.
- [SDK Integration Guide](guides/SDK_GUIDE.md): Developer guide for integrating Python (`agentguard`) and TypeScript (`@agentguard/sdk`) clients with LangChain and CrewAI.
- [Testing & Verification Guide](guides/TESTING_GUIDE.md): Detailed testing guide for executing the 173-test backend regression run, frontend builds, and SDK validation.

---

## 2. Architecture & System Design

- [Architecture Overview](architecture/README.md): High-level system architecture, client/control/execution layers, and core subsystems.
- [Master System Flow & Operational Specification](architecture/AGENTGUARD_MASTER_SYSTEM_FLOW.md): Authoritative 27-section master architectural specification covering the 18-stage governance kernel, actor taxonomies, and cryptographic identity.

---

## 3. Security, IAM & Governance

- [Security & IAM Index](security/README.md): Overview of zero-trust runtime interception, multi-tenant boundaries, and cryptographic audit guarantees.
- [Enterprise IAM & Permission Matrix](security/IAM_ROLE_MATRIX.md): Detailed specification of the canonical 5-role organizational IAM model (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`) and the global platform operator (`SUPER_ADMIN`).
- [Root Security Policy](../SECURITY.md): Vulnerability disclosure procedures, reporting contacts, and supported versions.

---

## 4. Evaluation & Benchmarking

- [Evaluation Lab Index](evaluation/README.md): Overview of the synthetic benchmark evaluation suite and adversarial test categories.
- [Dynamic Dataset & Benchmark Evaluation](evaluation/DATASET_EVALUATION.md): Guide to persistent dataset schemas, prompt injection benchmarks, metric calculation, and evaluation runs.

---

## 5. Specifications & Design Standards

- [Specifications Index](specifications/README.md): Directory of functional, UI, and architectural specifications.
- [UI Design System Specification](specifications/UI_DESIGN_SYSTEM.md): Visual design standards, Times New Roman typography, color tokens, and component guidelines.
- [Complete UI Page Directory](specifications/UI_PAGE_DIRECTORY.md): Catalog of all 59 frontend pages, routes, and access controls.
- [Functional Requirements Catalog](specifications/FUNCTIONAL_REQUIREMENTS.md): System functional specifications covering all control plane modules.
- [Master Feature Matrix](specifications/MASTER_FEATURE_MATRIX.md): Comprehensive feature and capability matrix.

---

## 6. Operations & Deployment Runbooks

- [Runbooks Index](runbooks/README.md): Operational guide directory.
- [Production Deployment Runbook](runbooks/DEPLOYMENT_RUNBOOK.md): Production deployment architecture, Docker containers, PostgreSQL/Supabase database setup, Redis brokers, and Celery workers.
- [Local Development Workflow](runbooks/DEVELOPMENT_WORKFLOW.md): Daily development procedures for Windows and UNIX systems.

---

## 7. Audit & Verification Reports

- [Reports Directory Index](reports/README.md): Catalog of all authoritative milestone audits and verification records.
- [Cleanup & Production Consistency Report](reports/CLEANUP_AND_PRODUCTION_CONSISTENCY_REPORT.md): Authoritative report on repository cleanup, demo data removal, 5-role IAM alignment, and regression suite pass.
- [Secret Remediation & Deployment Report](reports/PHASE_SECRET_REMEDIATION_REPORT.md): Audit confirming zero secrets tracked in Git and environment hygiene.
- [Deployment Configuration Fix Report](reports/PHASE_DEPLOYMENT_FIX_REPORT.md): Infrastructure fixes for Render, Vercel, and Docker Compose.
