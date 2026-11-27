"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Shield, Lock, Key, Users, Database, Activity, Zap, FileSearch, AlertTriangle,
  CheckCircle2, Clock, XCircle, Info, ChevronDown, ChevronUp, Eye
} from "lucide-react";

type StatusType = "implemented" | "implemented-unverified" | "planned" | "not-implemented";

interface SecurityItem {
  title: string;
  status: StatusType;
  description: string;
  detail?: string;
}

const StatusBadge = ({ status }: { status: StatusType }) => {
  const map: Record<StatusType, { label: string; className: string; icon: React.ReactNode }> = {
    "implemented": {
      label: "Implemented & Verified",
      className: "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30",
      icon: <CheckCircle2 className="w-3 h-3" />
    },
    "implemented-unverified": {
      label: "Implemented — Not Independently Verified",
      className: "bg-[#FFF4D9] text-[#B76E00] border-[#F59A23]/30",
      icon: <Clock className="w-3 h-3" />
    },
    "planned": {
      label: "Planned",
      className: "bg-[#EEF4FF] text-[#2878D4] border-[#2878D4]/30",
      icon: <Info className="w-3 h-3" />
    },
    "not-implemented": {
      label: "Not Implemented",
      className: "bg-[#F5F5F5] text-[#666666] border-[#CCCCCC]",
      icon: <XCircle className="w-3 h-3" />
    },
  };
  const cfg = map[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold border ${cfg.className}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
};

function SecuritySection({ icon, title, items }: { icon: React.ReactNode; title: string; items: SecurityItem[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
        <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center shrink-0">
          {icon}
        </div>
        <h2 className="text-[18px] font-bold text-[#1F1F1F]">{title}</h2>
      </div>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] overflow-hidden">
            <button
              onClick={() => setExpanded(expanded === i ? null : i)}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-[#FCFCFA] transition-colors"
            >
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[14px] font-bold text-[#1F1F1F]">{item.title}</span>
                <StatusBadge status={item.status} />
              </div>
              {expanded === i ? <ChevronUp className="w-4 h-4 text-[#666666] shrink-0" /> : <ChevronDown className="w-4 h-4 text-[#666666] shrink-0" />}
            </button>
            {expanded === i && (
              <div className="px-4 pb-4 border-t border-[#E8E8E4] pt-3 space-y-2">
                <p className="text-[13px] text-[#555555] leading-relaxed">{item.description}</p>
                {item.detail && (
                  <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[12px] font-mono text-[#444444] leading-relaxed">
                    {item.detail}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ZeroTrustSecurityPage() {
  return (
    <div className="min-h-screen bg-[#FCFCFA] text-[#1F1F1F] font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#FCFCFA]/90 backdrop-blur-md border-b border-[#E8E8E4]">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-[8px] bg-[#EAF7EE] border border-[#2E9D50]/30 flex items-center justify-center p-1.5 group-hover:border-[#2E9D50] transition-colors">
              <Image src="/logo.png" alt="AGENTGUARD Logo" width={28} height={28} className="object-contain" />
            </div>
            <span className="text-[16px] font-bold text-[#1F1F1F] tracking-tight">AGENTGUARD</span>
          </Link>
          <div className="flex items-center gap-4 text-[13px]">
            <Link href="/privacy" className="text-[#666666] hover:text-[#1F1F1F] transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="text-[#666666] hover:text-[#1F1F1F] transition-colors">Terms of Service</Link>
            <Link href="/login" className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[8px] transition-colors text-[12px]">Sign In</Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-14 pb-10 border-b border-[#E8E8E4] bg-[#FFFFFF]">
        <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-[10px] bg-[#EAF7EE] border border-[#2E9D50]/30 flex items-center justify-center">
              <Shield className="w-5 h-5 text-[#237A3C]" />
            </div>
            <div>
              <h1 className="text-[28px] sm:text-[34px] font-bold text-[#1F1F1F] tracking-tight leading-tight">Zero-Trust Security Architecture</h1>
              <p className="text-[13px] text-[#666666] mt-0.5">Last reviewed: November 2025 · Technical accuracy: verified from source code</p>
            </div>
          </div>
          <p className="text-[15px] text-[#555555] leading-relaxed max-w-3xl">
            AGENTGUARD enforces security at every layer — from HTTP request authorization through database row-level isolation. This page documents the actual implemented security architecture with verified status classifications.
          </p>

          {/* Status Legend */}
          <div className="mt-6 p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[12px]">
            <p className="text-[12px] font-bold text-[#1F1F1F] mb-3">Status Classifications</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[12px]">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#237A3C]" />
                <span className="font-bold text-[#237A3C]">Implemented & Verified</span>
                <span className="text-[#666666]">— confirmed from source code review</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-[#B76E00]" />
                <span className="font-bold text-[#B76E00]">Implemented — Not Independently Verified</span>
                <span className="text-[#666666]">— code exists, not independently tested</span>
              </div>
              <div className="flex items-center gap-2">
                <Info className="w-3.5 h-3.5 text-[#2878D4]" />
                <span className="font-bold text-[#2878D4]">Planned</span>
                <span className="text-[#666666]">— on the roadmap, not yet built</span>
              </div>
              <div className="flex items-center gap-2">
                <XCircle className="w-3.5 h-3.5 text-[#666666]" />
                <span className="font-bold text-[#666666]">Not Implemented</span>
                <span className="text-[#666666]">— not currently in the platform</span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-4 bg-[#FFF4D9] border border-[#F59A23]/30 rounded-[10px] flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-[#B76E00] mt-0.5 shrink-0" />
            <p className="text-[12px] text-[#7A5000] leading-relaxed">
              <strong>Disclosure:</strong> AGENTGUARD has not undergone formal penetration testing, SOC 2 audit, ISO 27001 certification, or independent third-party security review as of this writing. The &ldquo;Implemented & Verified&rdquo; classification refers to internal code-level review only. We do not claim zero-trust certification or any formal compliance standard. Organizations handling regulated data should conduct independent security assessments before production deployment.
            </p>
          </div>
        </div>
      </section>

      {/* Architecture Pipeline Overview */}
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <h2 className="text-[20px] font-bold text-[#1F1F1F] mb-5">Security Execution Pipeline</h2>
        <div className="grid grid-cols-3 md:grid-cols-9 gap-2 text-center text-[11px] font-bold mb-10">
          {[
            { n: "01", label: "Identity", color: "#2878D4" },
            { n: "02", label: "Auth Token", color: "#2878D4" },
            { n: "03", label: "Authorization", color: "#2878D4" },
            { n: "04", label: "Tenant Scope", color: "#F59A23" },
            { n: "05", label: "Policy Check", color: "#8064C8" },
            { n: "06", label: "Risk Score", color: "#8064C8" },
            { n: "07", label: "Decision", color: "#237A3C" },
            { n: "08", label: "Execution", color: "#237A3C" },
            { n: "09", label: "Audit Write", color: "#237A3C" },
          ].map((step) => (
            <div key={step.n} className="p-2 sm:p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="block font-mono text-[10px]" style={{ color: step.color }}>{step.n}</span>
              <span className="block text-[10px] text-[#1F1F1F]">{step.label}</span>
            </div>
          ))}
        </div>

        <div className="space-y-10">

          <SecuritySection
            icon={<Key className="w-4 h-4 text-[#237A3C]" />}
            title="Authentication"
            items={[
              {
                title: "JWT Authentication with Local Secret + Supabase Fallback",
                status: "implemented",
                description: "Every authenticated API request verifies the JWT using a local signing secret first (fast path). If that fails, falls back to Supabase API token verification. Both paths enforce signature validity and token expiry.",
                detail: "Implementation: backend/core/deps.py — get_current_user(). No credential bypass paths exist. GUC-based superadmin bypass is NOT present."
              },
              {
                title: "OTP-Based Email Verification at Registration",
                status: "implemented",
                description: "Account creation requires a 6-digit OTP sent to the registered email address. OTPs expire after 10 minutes, are invalidated on use, and have a cooldown period to prevent abuse.",
                detail: "Implementation: backend/routers/auth.py — register/request-otp and register/verify-otp endpoints. Cooldown enforced server-side."
              },
              {
                title: "Session Revocation Check",
                status: "implemented",
                description: "On each authenticated request, the system checks whether the user's session has been explicitly revoked (e.g., via admin suspension). Revoked sessions are rejected regardless of token validity.",
                detail: "Implementation: backend/core/deps.py — session_revoked check in get_current_user()."
              },
              {
                title: "Account Status Check",
                status: "implemented",
                description: "Users with SUSPENDED account status are rejected at the authentication layer even if they present a valid JWT token.",
                detail: "Implementation: backend/core/deps.py — account_status == ACTIVE enforcement."
              },
              {
                title: "Token Cache",
                status: "implemented-unverified",
                description: "JWT verification results are cached to reduce repeated Supabase API calls on high-frequency requests. Cache entries are invalidated on session revocation. Not independently load-tested.",
              },
              {
                title: "Multi-Factor Authentication (MFA)",
                status: "planned",
                description: "TOTP-based MFA (authenticator app) for high-privilege accounts (ADMIN, SUPER_ADMIN) is on the product roadmap. Currently only OTP email verification is implemented.",
              },
            ]}
          />

          <SecuritySection
            icon={<Users className="w-4 h-4 text-[#237A3C]" />}
            title="Authorization & IAM"
            items={[
              {
                title: "9-Tier Role-Based Access Control (RBAC)",
                status: "implemented",
                description: "AGENTGUARD enforces a strict 9-tier IAM hierarchy: VIEWER, ANALYST, USER, OPERATOR, DEVELOPER, MANAGER, COMPLIANCE_OFFICER, ADMIN, and SUPER_ADMIN. Each role has precisely defined route and resource permissions enforced server-side.",
                detail: "Implementation: backend/core/deps.py — require_role(), require_admin(), require_manager(), require_super_admin(). Frontend: lib/permissions.ts — hasRoutePermission()."
              },
              {
                title: "SUPER_ADMIN Platform Isolation",
                status: "implemented",
                description: "SUPER_ADMIN is a platform-level identity only. SUPER_ADMIN is never listed inside any organization's IAM user list. Switching to SUPER_ADMIN context requires platform-level authentication. SUPER_ADMIN cannot be assigned as an organization role.",
                detail: "Implementation: platform/layout.tsx enforces user.role === 'SUPER_ADMIN' gate. Backend require_super_admin() rejects any other role."
              },
              {
                title: "IDOR Protection on All Resource Endpoints",
                status: "implemented",
                description: "All resource-level endpoints (notifications, agents, security incidents) validate that the requesting user owns the resource before returning or modifying it. Cross-user access returns HTTP 403.",
                detail: "Implementation: notifications.py — user_id ownership check on GET /{id}, PATCH /{id}/read, DELETE /{id}. Returns 403 on cross-user access."
              },
              {
                title: "Route-Level Permission Enforcement",
                status: "implemented",
                description: "Frontend navigation is filtered by role using hasRoutePermission(). Backend enforces the same permissions independently — frontend permission hiding is a UX convenience, not a security boundary.",
              },
              {
                title: "Attribute-Based Access Control (ABAC)",
                status: "planned",
                description: "Fine-grained ABAC based on resource attributes (e.g., agent autonomy tier, risk score) beyond role-level RBAC is planned for future releases.",
              },
            ]}
          />

          <SecuritySection
            icon={<Database className="w-4 h-4 text-[#237A3C]" />}
            title="Tenant Isolation & Database Security"
            items={[
              {
                title: "SQL-Level Tenant Isolation (organization_id Filtering)",
                status: "implemented",
                description: "All multi-tenant data resources (users, agents, policies, notifications, audit logs, approvals, decisions) are filtered at the SQL query layer using organization_id. No cross-tenant data leakage is possible through the application API layer.",
                detail: "Implementation: All database queries in backend/routers/ and backend/services/ include organization_id == current_user.org_id filter for non-SUPER_ADMIN roles."
              },
              {
                title: "PostgreSQL Row-Level Security (RLS) Migration",
                status: "implemented-unverified",
                description: "PostgreSQL RLS policies are defined in migration files for Supabase-hosted PostgreSQL. These provide a database-layer backstop against SQL injection bypassing application-level filters. Not independently verified against a live Supabase production instance.",
                detail: "Implementation: backend/migrations/ — RLS policy migration files. Validation test suite: tests/test_postgresql_rls_validation.py (requires live PostgreSQL container)."
              },
              {
                title: "Parameterized Queries (SQL Injection Prevention)",
                status: "implemented",
                description: "All database queries use SQLAlchemy ORM with parameterized queries. No raw string interpolation into SQL is present in reviewed code. This prevents SQL injection attacks.",
                detail: "Implementation: SQLAlchemy ORM throughout backend/routers/ and backend/services/. No raw execute() with string interpolation found in audit."
              },
              {
                title: "No Credentials Exposed in API Responses",
                status: "implemented",
                description: "Platform health API endpoints that probe email and database configuration do not expose API keys, connection strings, passwords, or secrets in responses. Only boolean/status values are returned.",
                detail: "Implementation: backend/routers/platform.py — /health endpoint. email_service.get_status() returns {configured: bool, provider: str} only."
              },
            ]}
          />

          <SecuritySection
            icon={<Activity className="w-4 h-4 text-[#237A3C]" />}
            title="Runtime Governance Security"
            items={[
              {
                title: "Agent Capability Token Authorization",
                status: "implemented-unverified",
                description: "AI agents must present valid capability tokens scoped to specific resource targets and task types. Tokens are validated before any governance decision is processed. Not independently penetration-tested.",
              },
              {
                title: "Policy Engine Deterministic Evaluation",
                status: "implemented-unverified",
                description: "The runtime policy engine evaluates governance rules deterministically — the same input always produces the same ALLOW/REVIEW/REFUSE decision. Policy rules are configurable per organization. Not independently audited.",
              },
              {
                title: "Human Approval Workflow with Role Enforcement",
                status: "implemented",
                description: "High-risk agent operations requiring human review are routed to users with MANAGER or ADMIN roles. Approvals are recorded with approver identity and timestamp in the Decision Black Box. Only authorized approvers can submit decisions.",
                detail: "Implementation: backend/routers/approvals.py — role enforcement on approval submission. Notification triggered on approval/rejection."
              },
              {
                title: "Circuit Breaker (Agent Kill Switch)",
                status: "implemented",
                description: "Administrators can immediately suspend any AI agent. Suspension is recorded as a security event with governance notification emitted. Restoration requires explicit admin action and emits a separate restoration event.",
                detail: "Implementation: backend/routers/agents.py — suspend_agent() (line 341) and restore_agent() (line 411). Both emit correctly typed governance events."
              },
              {
                title: "Webhook DEAD_LETTER Deduplication Guard",
                status: "implemented",
                description: "Webhook delivery retries are guarded against creating duplicate dead-letter notifications. If a webhook is already in DEAD_LETTER state, the notification is not re-emitted.",
                detail: "Implementation: backend/tasks/webhook_tasks.py:42 — DEAD_LETTER status check before notification creation."
              },
            ]}
          />

          <SecuritySection
            icon={<Eye className="w-4 h-4 text-[#237A3C]" />}
            title="Security Monitoring & Incident Response"
            items={[
              {
                title: "Security Incident Management",
                status: "implemented",
                description: "Platform operators can create, track, update, and resolve security incidents. Incident creation and status changes (resolved/updated) emit governance notifications with correct event types and organization scoping.",
                detail: "Implementation: backend/routers/security.py — incident_created, incident_resolved, incident_updated events verified in source."
              },
              {
                title: "In-App Governance Notification System",
                status: "implemented",
                description: "All significant governance events (agent suspension, approval decisions, security incidents, webhook failures) generate in-app notifications scoped to the relevant user. Notifications include severity levels: INFO, WARNING, HIGH, CRITICAL.",
                detail: "Implementation: backend/services/notification_service.py + backend/tasks/notification_tasks.py."
              },
              {
                title: "Email-Independent Notification Persistence",
                status: "implemented",
                description: "Email delivery failures do not block in-app notification persistence. If email delivery fails, the in-app notification is still created and stored.",
                detail: "Implementation: Email failures are caught independently in notification_service.py. In-app notification is committed to DB before email is attempted."
              },
              {
                title: "Causal Audit Provenance",
                status: "implemented-unverified",
                description: "Every agent action is traced to its originating user, agent version, capability token, and policy rule evaluation. This creates a complete forensic audit trail. Full end-to-end provenance not independently verified.",
              },
              {
                title: "Formal Security Information & Event Management (SIEM) Integration",
                status: "planned",
                description: "Integration with external SIEM systems (Splunk, Datadog, etc.) for real-time security event streaming is planned but not yet implemented.",
              },
            ]}
          />

          <SecuritySection
            icon={<Lock className="w-4 h-4 text-[#237A3C]" />}
            title="API & Network Security"
            items={[
              {
                title: "CORS Configuration",
                status: "implemented-unverified",
                description: "The FastAPI backend configures CORS headers. Exact allowed origins should be verified and restricted to production frontend domains before launch. Not independently audited.",
              },
              {
                title: "HTTPS Enforcement",
                status: "implemented-unverified",
                description: "HTTPS is enforced by the hosting platforms (Vercel for frontend, Render for backend). Direct HTTP connections are redirected to HTTPS. Not independently tested.",
              },
              {
                title: "Rate Limiting",
                status: "planned",
                description: "Platform-level API rate limiting per user and organization is planned. Currently only OTP cooldown rate limiting is implemented.",
              },
              {
                title: "Web Application Firewall (WAF)",
                status: "not-implemented",
                description: "No dedicated WAF is currently deployed in front of the AGENTGUARD API. Organizations with high-security requirements should implement a WAF at the infrastructure level.",
              },
              {
                title: "Pagination Bounds Enforcement",
                status: "implemented",
                description: "All list API endpoints enforce pagination bounds (minimum 1, maximum 200 items per request) to prevent API abuse and denial-of-service via unbounded queries.",
                detail: "Implementation: notifications router Query(ge=1, le=200) on limit parameter."
              },
            ]}
          />

          <SecuritySection
            icon={<Zap className="w-4 h-4 text-[#237A3C]" />}
            title="Credential & Secret Management"
            items={[
              {
                title: "Environment Variable Secret Management",
                status: "implemented-unverified",
                description: "All secrets (JWT signing keys, database connection strings, email API keys) are stored as environment variables and never committed to version control. Render and Vercel provide encrypted environment variable storage.",
              },
              {
                title: "No Secrets in API Responses",
                status: "implemented",
                description: "Platform health, integrations, and status endpoints do not include any secret values, API keys, connection strings, or credentials in their JSON responses.",
                detail: "Verified in backend/routers/platform.py health endpoint audit."
              },
              {
                title: "Formal Secret Rotation Policy",
                status: "not-implemented",
                description: "Automated secret rotation (e.g., rotating JWT signing keys, database passwords on a schedule) is not currently implemented. The platform owner should establish a manual rotation schedule and automate it before production.",
              },
            ]}
          />

          <SecuritySection
            icon={<FileSearch className="w-4 h-4 text-[#237A3C]" />}
            title="Compliance & Certifications"
            items={[
              {
                title: "Internal Code-Level Security Audit",
                status: "implemented",
                description: "AGENTGUARD has undergone internal code-level security review covering authentication, authorization, tenant isolation, IDOR, SQL injection, and dummy data. See docs/audits/ for detailed audit reports.",
              },
              {
                title: "Automated Security Test Suite",
                status: "implemented",
                description: "Automated test suites covering: P0 security remediations, tenant isolation, authentication flows, RLS validation, runtime security invariants, and truthfulness assertions. 99 tests pass as of November 2025.",
                detail: "Test files: test_p0_security_remediation.py, test_tenant_isolation_and_security_audit.py, test_authentication_and_otp_flows.py, test_postgresql_rls_validation.py, test_runtime_security_invariants.py."
              },
              {
                title: "Independent Penetration Testing",
                status: "not-implemented",
                description: "No formal third-party penetration test has been conducted. This is recommended before production deployment, particularly for organizations handling sensitive operational AI data.",
              },
              {
                title: "SOC 2 Type II",
                status: "not-implemented",
                description: "AGENTGUARD does not currently hold SOC 2 certification. Organizations requiring SOC 2 compliance from their SaaS vendors should not rely on this platform in that capacity until certification is achieved.",
              },
              {
                title: "ISO 27001",
                status: "not-implemented",
                description: "No ISO 27001 certification exists for the AGENTGUARD platform. This should not be claimed in marketing materials.",
              },
              {
                title: "GDPR Data Processing Agreement (DPA)",
                status: "planned",
                description: "Organizations in the EU processing personal data through AGENTGUARD will require a formal Data Processing Agreement. This is planned but not yet formalized.",
              },
            ]}
          />

        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-[#E8E8E4] bg-[#FFFFFF] py-8 mt-8">
        <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[12px] text-[#666666]">
          <span>© {new Date().getFullYear()} AGENTGUARD. All rights reserved.</span>
          <div className="flex items-center gap-6">
            <Link href="/privacy" className="hover:text-[#1F1F1F] transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-[#1F1F1F] transition-colors">Terms of Service</Link>
            <Link href="/security" className="text-[#2E9D50] font-bold">Zero-Trust Security</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
