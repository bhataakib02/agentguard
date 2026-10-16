# Security Policy & Vulnerability Disclosure

AGENTGUARD is an enterprise-grade runtime security control plane and governance firewall for autonomous AI agents. We take the security, integrity, and privacy of our systems, SDKs, and users with extreme seriousness.

This document describes our vulnerability reporting procedure, supported releases, and responsible disclosure expectations.

---

## 1. Supported Versions

Security updates, vulnerability patches, and CVE remediation are actively provided for the following releases:

| Component | Version | Security Support Status |
| :--- | :--- | :---: |
| **AGENTGUARD Control Plane (Backend & API)** | `v1.0.x` | Supported (Current Stable) |
| **AGENTGUARD Enterprise Dashboard (Frontend)** | `v1.0.x` | Supported (Current Stable) |
| **AGENTGUARD Python SDK (`agentguard`)** | `>= 1.0.0` | Supported (Current Stable) |
| **AGENTGUARD TypeScript SDK (`@agentguard/sdk`)** | `>= 1.0.0` | Supported (Current Stable) |
| Pre-release / Experimental Branches | `< 1.0.0` | Best Effort / Upgrade Recommended |

---

## 2. Reporting a Security Vulnerability

If you discover a security vulnerability, authorization bypass, cryptographic weakness, tenant leakage, or execution sandboxing flaw in AGENTGUARD, **please do not open a public GitHub issue or discuss it in public channels.**

### 2.1 Private Reporting Procedure

1. **Email Contact:** Send your disclosure report to our dedicated security inbox:  
   `security@agentguard.dev`
2. **Subject Line:** Format your email subject with clear context:  
   `[SECURITY DISCLOSURE] Brief summary of vulnerability (e.g., JWT Session Invalidation Bypass)`
3. **Report Contents:** To help us triage and remediate the issue rapidly, please include:
   - Specific component and version affected (e.g., Backend, PACE Engine, SDK, Dashboard).
   - Detailed step-by-step reproduction instructions or a minimal proof-of-concept (PoC).
   - Attack vector, threat model impact, and affected IAM roles or data assets.
   - Any suggested mitigations or candidate patches, if available.
   - Optional: Your name, handle, or organization for public security advisory attribution.

---

## 3. Vulnerability Response Timeline

Our security engineering team adheres to the following response targets:

1. **Initial Acknowledgment:** Within **48 hours** of receiving your report, confirming receipt and initiating internal assessment.
2. **Triaging & Reproduction:** Within **5 business days**, validating the report, assigning a severity rating (CVSS v3.1), and establishing scope.
3. **Remediation & Patch Development:** High and critical severity issues receive emergency engineering priority. We will provide regular status updates during patch development.
4. **Coordinated Disclosure:** We kindly request a standard **90-day responsible disclosure window** to allow coordinated release of security patches across deployed systems before public disclosure.

---

## 4. Responsible Disclosure Guidelines

To protect AGENTGUARD deployments and users in production environments:

1. **Do not exploit security issues beyond verification:** Conduct testing only to the minimum extent necessary to establish a proof of concept.
2. **Do not access or modify tenant data:** Never access, exfiltrate, corrupt, or modify customer data, production databases, or credentials belonging to other organizations.
3. **Do not execute disruptive tests:** Do not perform distributed denial-of-service (DDoS), spamming, brute-force credential stuffing, or destructive attacks against public services or demonstration environments.
4. **Preserve confidentiality:** Maintain mutual confidentiality regarding vulnerability details until a remediation release has been published.

---

## 5. Security Architecture Invariants

For security researchers and auditors reviewing AGENTGUARD source code:

1. **Canonical 5-Role IAM:** Organization tenant boundaries strictly enforce five roles (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`). Any mechanism allowing a tenant user to acquire `SUPER_ADMIN` privileges or access cross-tenant data represents a critical vulnerability.
2. **PACE Runtime Control:** Every autonomous tool execution must pass Predictive Action Control Engine (PACE) evaluation (`ALLOW`, `REVIEW`, `REFUSE`). Bypassing the PACE execution gate constitutes a high-severity finding.
3. **Cryptographic Audit Integrity:** Audit logs incorporate SHA-256 hash chains (`previous_hash` $\to$ `record_hash`). Any vulnerability permitting unsigned or undetected audit log tampering is considered critical.
4. **Token & Key Revocation:** Revoked session tokens, disabled API keys, and rotated secrets must invalidate active sessions immediately via Redis blacklist or database session checks.

Thank you for helping keep AGENTGUARD and the AI agent ecosystem secure!
