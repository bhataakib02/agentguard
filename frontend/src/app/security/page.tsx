import type { Metadata } from "next";
import LegalDocShell, {
  DocSection,
  SecurityCapabilityStatus,
  SecurityStatusBadge,
  TocItem,
} from "@/components/legal/LegalDocShell";

export const metadata: Metadata = {
  title: "Zero-Trust Security Architecture | AGENTGUARD",
  description:
    "Technical security documentation for AGENTGUARD: authentication, RBAC, tenant isolation, runtime policy enforcement, database security, and capability status.",
};

const TOC: TocItem[] = [
  { id: "security-philosophy", number: "1", title: "Security Philosophy" },
  { id: "zero-trust-architecture", number: "2", title: "Zero-Trust Architecture" },
  { id: "iam", number: "3", title: "Identity and Access Management" },
  { id: "auth-session-security", number: "4", title: "Authentication and Session Security" },
  { id: "rbac", number: "5", title: "Role-Based Access Control" },
  { id: "tenant-isolation", number: "6", title: "Organization and Tenant Isolation" },
  { id: "agent-identity-authz", number: "7", title: "AI Agent Identity and Authorization" },
  { id: "runtime-policy-enforcement", number: "8", title: "Runtime Policy Enforcement" },
  { id: "api-security", number: "9", title: "API Security" },
  { id: "token-secret-management", number: "10", title: "Token and Secret Management" },
  { id: "database-security", number: "11", title: "Database Security" },
  { id: "encryption", number: "12", title: "Encryption at Rest and in Transit" },
  { id: "audit-logging-monitoring", number: "13", title: "Audit Logging and Monitoring" },
  { id: "incident-response", number: "14", title: "Security Incident Response" },
  { id: "vulnerability-management", number: "15", title: "Vulnerability Management" },
  { id: "retention-deletion", number: "16", title: "Data Retention and Deletion" },
  { id: "infrastructure-hosting", number: "17", title: "Infrastructure and Hosting Security" },
  { id: "third-party-integrations", number: "18", title: "Third-Party Integrations" },
  { id: "backup-recovery", number: "19", title: "Backup and Recovery" },
  { id: "responsible-disclosure", number: "20", title: "Responsible Disclosure & Reporting" },
  { id: "security-contact", number: "21", title: "Security Contact" },
];

function CapabilityRow({
  title,
  status,
  summary,
}: {
  title: string;
  status: SecurityCapabilityStatus;
  summary: string;
}) {
  return (
    <div className="p-4 border border-[#E8E8E4] rounded-[8px] bg-[#FCFCFA] space-y-2">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <span className="font-bold text-[#141414] text-[14px]">{title}</span>
        <SecurityStatusBadge status={status} />
      </div>
      <p className="text-[13px] text-[#444444] leading-relaxed">{summary}</p>
    </div>
  );
}

export default function ZeroTrustSecurityPage() {
  return (
    <LegalDocShell
      activeRoute="/security"
      breadcrumbLabel="Zero-Trust Security"
      title="Zero-Trust Security Architecture"
      description="Technical security documentation for AGENTGUARD detailing implemented controls, architectural boundaries, infrastructure dependencies, and verification status."
      lastUpdated="November 27, 2026"
      version="2.0 (Technical Reference — Code-Verified)"
      toc={TOC}
    >
      <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-3">
        <div className="text-[13px] font-bold text-[#141414]">
          Capability Classification Legend
        </div>
        <div className="flex flex-wrap gap-2">
          <SecurityStatusBadge status="implemented-verified" />
          <SecurityStatusBadge status="implemented-unverified" />
          <SecurityStatusBadge status="partially-implemented" />
          <SecurityStatusBadge status="planned" />
          <SecurityStatusBadge status="not-implemented" />
        </div>
        <p className="text-[12.5px] text-[#555555] leading-relaxed">
          AGENTGUARD does not currently hold SOC 2 Type II, ISO 27001, GDPR certification, or a completed third-party penetration test. Controls classified below as &ldquo;Implemented but not independently verified&rdquo; are verified by internal source inspection and automated test suites, not by an external auditor.
        </p>
      </div>

      <DocSection id="security-philosophy" number="1" title="Security Philosophy">
        <p>
          AGENTGUARD is designed around explicit verification at every boundary: no user, AI agent, or service call is trusted by network location or client-side state alone. Every API request is authenticated, authorized against server-side IAM roles, scoped to an organization tenant, and recorded in immutable audit logs where applicable.
        </p>
      </DocSection>

      <DocSection id="zero-trust-architecture" number="2" title="Zero-Trust Architecture">
        <p>Requests traversing the AGENTGUARD control plane pass through layered enforcement:</p>
        <ol className="list-decimal pl-5 space-y-1.5">
          <li><strong>Identity &amp; Token Verification:</strong> JWT validation with signature, expiry, session revocation, and account status checks (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">backend/core/deps.py</code>).</li>
          <li><strong>Tenant &amp; Role Authorization:</strong> Server-side <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">org_id</code> scoping and 9-tier RBAC checks.</li>
          <li><strong>Runtime Governance Pipeline:</strong> Agent Passport validation, deterministic policy evaluation, dynamic risk scoring, and human approval routing or circuit-breaker refusal.</li>
          <li><strong>Audit &amp; Provenance:</strong> Structured audit logging without secret or credential leakage.</li>
        </ol>
      </DocSection>

      <DocSection id="iam" number="3" title="Identity and Access Management">
        <CapabilityRow
          title="9-Tier Organization IAM Hierarchy & SUPER_ADMIN Isolation"
          status="implemented-unverified"
          summary="Enforces VIEWER, ANALYST, USER, OPERATOR, DEVELOPER, MANAGER, COMPLIANCE_OFFICER, ADMIN, and platform-isolated SUPER_ADMIN roles. SUPER_ADMIN is never exposed inside organization IAM user directories."
        />
        <CapabilityRow
          title="Registration & Passwordless OTP Email Verification"
          status="implemented-unverified"
          summary="Six-digit cryptographic OTPs generated with secrets.randbelow, stored as keyed HMAC-SHA256 digests with 10-minute expiry, 5-attempt limit, 120-second resend cooldown, and per-IP/per-email rate limiting."
        />
      </DocSection>

      <DocSection id="auth-session-security" number="4" title="Authentication and Session Security">
        <CapabilityRow
          title="JWT Verification & Session Revocation"
          status="implemented-unverified"
          summary="Validates JWTs using local secret verification with Supabase Auth API fallback, checks server-side session revocation, and rejects SUSPENDED accounts."
        />
        <CapabilityRow
          title="Authenticator-App MFA (TOTP / WebAuthn)"
          status="planned"
          summary="Hardware or TOTP-based multi-factor authentication for privileged ADMIN and SUPER_ADMIN accounts is planned and not yet implemented."
        />
      </DocSection>

      <DocSection id="rbac" number="5" title="Role-Based Access Control">
        <CapabilityRow
          title="Server-Side RBAC & IDOR Ownership Checks"
          status="implemented-unverified"
          summary="Every protected router enforces role dependencies (require_admin, require_manager, require_super_admin) and resource ownership checks (returning HTTP 403 on cross-user notification or resource access)."
        />
        <CapabilityRow
          title="Fine-Grained Attribute-Based Access Control (ABAC)"
          status="planned"
          summary="Policy-driven ABAC beyond role and organization boundaries is planned for future releases."
        />
      </DocSection>

      <DocSection id="tenant-isolation" number="6" title="Organization and Tenant Isolation">
        <CapabilityRow
          title="Application-Layer SQL Tenant Scoping"
          status="implemented-unverified"
          summary="Multi-tenant queries filter by organization_id/org_id derived from the authenticated user context. Cross-tenant access attempts fail closed."
        />
        <CapabilityRow
          title="PostgreSQL Row-Level Security (RLS) Policies"
          status="partially-implemented"
          summary="RLS SQL migrations and automated PostgreSQL validation tests exist in the repository; live enforcement depends on applying migrations and running the suite against the target PostgreSQL 17/Supabase instance."
        />
      </DocSection>

      <DocSection id="agent-identity-authz" number="7" title="AI Agent Identity and Authorization">
        <CapabilityRow
          title="Agent Passports & Capability Tokens"
          status="implemented-unverified"
          summary="Each AI agent receives a scoped passport defining owner, allowed tasks, autonomy tier, and daily budget limits, paired with capability token validation and revocation endpoints."
        />
      </DocSection>

      <DocSection id="runtime-policy-enforcement" number="8" title="Runtime Policy Enforcement">
        <CapabilityRow
          title="Deterministic Policy Engine, Risk Scoring & Kill Switch"
          status="implemented-unverified"
          summary="Evaluates ALLOW / REVIEW / REFUSE outcomes, computes 0-100 risk scores, routes high-risk actions to MANAGER/ADMIN approvals, and supports immediate agent suspension via circuit breaker."
        />
      </DocSection>

      <DocSection id="api-security" number="9" title="API Security">
        <CapabilityRow
          title="Pagination Bounds, Trusted Hosts & CORS"
          status="implemented-unverified"
          summary="Enforces bounded pagination (e.g., max 200 items), TrustedHostMiddleware in production, and configured CORS origins."
        />
        <CapabilityRow
          title="Global Platform API Rate Limiting & WAF"
          status="partially-implemented"
          summary="Rate limiting is implemented on OTP/auth endpoints; global per-tenant API rate limiting is planned and no dedicated WAF is currently deployed."
        />
      </DocSection>

      <DocSection id="token-secret-management" number="10" title="Token and Secret Management">
        <CapabilityRow
          title="Environment Secret Isolation & Redacted Health Probes"
          status="implemented-unverified"
          summary="Production startup fails closed if SECRET_KEY is missing or insecure. Health and integration probes return configuration booleans/provider names without exposing API keys, passwords, or connection strings."
        />
        <CapabilityRow
          title="Automated Key Rotation"
          status="not-implemented"
          summary="Automated scheduled rotation of signing keys and third-party API secrets is not implemented; keys are rotated manually via environment configuration."
        />
      </DocSection>

      <DocSection id="database-security" number="11" title="Database Security">
        <CapabilityRow
          title="Parameterized ORM Queries & Production DB Guard"
          status="implemented-unverified"
          summary="Database access uses SQLAlchemy ORM parameterized queries. Production configuration prohibits silent fallback to SQLite and disables automatic startup DDL migrations."
        />
      </DocSection>

      <DocSection id="encryption" number="12" title="Encryption at Rest and in Transit">
        <CapabilityRow
          title="TLS in Transit & Ephemeral AES-256-GCM Encryption"
          status="implemented-unverified"
          summary="HTTPS/TLS is enforced by Vercel and Render edge infrastructure, and outbound Resend/Brevo/SMTP calls use TLS. Pending registration credentials are encrypted in-app with AES-256-GCM and scrubbed upon verification. Database encryption at rest relies on Supabase/PostgreSQL hosting defaults."
        />
      </DocSection>

      <DocSection id="audit-logging-monitoring" number="13" title="Audit Logging and Monitoring">
        <CapabilityRow
          title="Audit Logs, Decision Black Box & Sanitized Email Telemetry"
          status="implemented-unverified"
          summary="Records authentication events, agent actions, approvals, and email dispatch correlation IDs without logging OTPs, passwords, or API keys. External SIEM forwarding hooks are implemented in configuration but require customer SIEM endpoints."
        />
      </DocSection>

      <DocSection id="incident-response" number="14" title="Security Incident Response">
        <CapabilityRow
          title="Incident Tracking & Governance Notifications"
          status="implemented-unverified"
          summary="Supports security incident creation, status transitions, kill-switch suspension, and in-app/email alerting with webhook dead-letter deduplication."
        />
      </DocSection>

      <DocSection id="vulnerability-management" number="15" title="Vulnerability Management">
        <CapabilityRow
          title="Independent Penetration Testing & Continuous Dependency Scanning"
          status="not-implemented"
          summary="No formal third-party penetration test or automated vulnerability SLA program has been completed."
        />
      </DocSection>

      <DocSection id="retention-deletion" number="16" title="Data Retention and Deletion">
        <CapabilityRow
          title="Configurable Retention Windows & Automated Purge Jobs"
          status="partially-implemented"
          summary="Retention settings (audit, telemetry, expired sessions) are defined in backend configuration and OTP challenges expire after 10 minutes; automated background purge enforcement across all historical tables is planned."
        />
      </DocSection>

      <DocSection id="infrastructure-hosting" number="17" title="Infrastructure and Hosting Security">
        <p>
          AGENTGUARD runs on Vercel (Next.js frontend), Render (FastAPI backend, Celery workers, and Redis), and Supabase (PostgreSQL and authentication). Physical data-center controls and SOC 2/ISO certifications of those underlying vendors are governed by their respective trust programs and do not constitute certification of AGENTGUARD itself.
        </p>
      </DocSection>

      <DocSection id="third-party-integrations" number="18" title="Third-Party Integrations">
        <p>
          Transactional email delivery supports Brevo (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">api.brevo.com</code>), Resend (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">api.resend.com</code>), and TLS-enabled SMTP with explicit 10-second timeouts, strict error classification, and no ambiguous cross-provider retries.
        </p>
      </DocSection>

      <DocSection id="backup-recovery" number="19" title="Backup and Recovery">
        <CapabilityRow
          title="Managed Database Backups & Verified Restore Drills"
          status="partially-implemented"
          summary="Database backups depend on the underlying Supabase PostgreSQL plan; documented RPO/RTO targets and periodic restore drills are not yet formalized."
        />
      </DocSection>

      <DocSection id="responsible-disclosure" number="20" title="Responsible Disclosure and Vulnerability Reporting">
        <p>
          We welcome responsible security reports from researchers and customers. Please do not test against production customer tenants, exfiltrate data, or disrupt service availability. Include clear reproduction steps and impact details when reporting an issue.
        </p>
      </DocSection>

      <DocSection id="security-contact" number="21" title="Security Contact">
        <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[13.5px]">
          <p><strong>Security Team Email:</strong> [COMPANY INFORMATION REQUIRED: Security Contact Email]</p>
          <p><strong>PGP Key / Security Advisory Channel:</strong> [COMPANY INFORMATION REQUIRED: Optional PGP Fingerprint or Disclosure Portal]</p>
        </div>
      </DocSection>
    </LegalDocShell>
  );
}
