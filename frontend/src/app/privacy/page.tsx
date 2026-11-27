"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { Shield, Lock, Database, Eye, Users, Mail, FileText, AlertTriangle, CheckCircle2, ExternalLink } from "lucide-react";

export default function PrivacyPolicyPage() {
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
            <Link href="/terms" className="text-[#666666] hover:text-[#1F1F1F] transition-colors">Terms of Service</Link>
            <Link href="/security" className="text-[#666666] hover:text-[#1F1F1F] transition-colors">Security</Link>
            <Link href="/login" className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[8px] transition-colors text-[12px]">Sign In</Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-14 pb-10 border-b border-[#E8E8E4] bg-[#FFFFFF]">
        <div className="max-w-[800px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-[10px] bg-[#EAF7EE] border border-[#2E9D50]/30 flex items-center justify-center">
              <Lock className="w-5 h-5 text-[#237A3C]" />
            </div>
            <div>
              <h1 className="text-[28px] sm:text-[34px] font-bold text-[#1F1F1F] tracking-tight leading-tight">Privacy Policy</h1>
              <p className="text-[13px] text-[#666666] mt-0.5">Effective date: November 2025 · Last reviewed: November 2025</p>
            </div>
          </div>
          <p className="text-[15px] text-[#555555] leading-relaxed">
            AGENTGUARD is an enterprise AI Agent Governance and Runtime Control Plane. This policy explains what data we collect, how we use it, and your rights regarding that data. We do not sell personal data.
          </p>
          <div className="mt-5 p-4 bg-[#FFF4D9] border border-[#F59A23]/30 rounded-[10px] flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-[#B76E00] mt-0.5 shrink-0" />
            <p className="text-[12px] text-[#7A5000] leading-relaxed">
              <strong>Legal Notice:</strong> This policy is provided for transparency purposes. AGENTGUARD is in active development. The platform owner should supplement this document with jurisdiction-specific legal counsel, a registered entity name, registered address, and applicable compliance certifications before entering production or processing personal data at scale.
            </p>
          </div>
        </div>
      </section>

      {/* Content */}
      <div className="max-w-[800px] mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">

        {/* 1. Who We Are */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Shield className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">1. Who We Are</h2>
          </div>
          <p className="text-[14px] text-[#555555] leading-relaxed">
            AGENTGUARD is a Software-as-a-Service platform for governing autonomous AI agents in enterprise environments. The platform provides agent identity management (Agent Passports), runtime policy enforcement, risk scoring, human-in-the-loop approval workflows, security incident management, audit provenance tracking, and notification services.
          </p>
          <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] text-[13px] text-[#555555] space-y-1">
            <p><strong className="text-[#1F1F1F]">Platform contact (privacy inquiries):</strong> Please contact the platform administrator using the contact information provided during your organization onboarding.</p>
            <p className="text-[12px] text-[#888888] mt-2">The platform owner must add their legal entity name, registered address, and a dedicated privacy contact email here before distributing this policy.</p>
          </div>
        </section>

        {/* 2. Data We Collect */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Database className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">2. Data We Collect</h2>
          </div>

          <div className="space-y-4">
            <div className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-2">
              <h3 className="text-[14px] font-bold text-[#1F1F1F]">2.1 Account & Authentication Data</h3>
              <ul className="text-[13px] text-[#555555] space-y-1 list-disc list-inside">
                <li>Full name and email address (collected at registration)</li>
                <li>Hashed password (never stored in plaintext; hashed by the authentication layer)</li>
                <li>OTP (one-time passcode) for email verification — stored temporarily, expires after 10 minutes</li>
                <li>Organization affiliation, IAM role (USER / MANAGER / ADMIN / SUPER_ADMIN)</li>
                <li>Session tokens (JWT) stored in browser cookies and localStorage with configurable expiry</li>
                <li>Last login timestamp</li>
                <li>Account status (ACTIVE / SUSPENDED / PENDING)</li>
              </ul>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-2">
              <h3 className="text-[14px] font-bold text-[#1F1F1F]">2.2 AI Agent Data</h3>
              <ul className="text-[13px] text-[#555555] space-y-1 list-disc list-inside">
                <li>Agent identity records (Agent ID, name, purpose, autonomy tier, capability tokens)</li>
                <li>Agent ownership and organization association</li>
                <li>Agent operational status (ACTIVE / SUSPENDED)</li>
                <li>Capability token grants and revocations</li>
                <li>Permission matrix configurations</li>
              </ul>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-2">
              <h3 className="text-[14px] font-bold text-[#1F1F1F]">2.3 Governance & Decision Records</h3>
              <ul className="text-[13px] text-[#555555] space-y-1 list-disc list-inside">
                <li>Policy engine evaluation records (resource target, transaction value, risk threshold)</li>
                <li>Runtime governance decisions (ALLOW / REVIEW / REFUSE) with rationale</li>
                <li>Human approval workflow records (approver identity, decision, timestamp)</li>
                <li>Risk scoring records (dynamic risk scores 0–100)</li>
                <li>Decision Black Box entries (immutable governance audit records)</li>
              </ul>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-2">
              <h3 className="text-[14px] font-bold text-[#1F1F1F]">2.4 Security & Incident Data</h3>
              <ul className="text-[13px] text-[#555555] space-y-1 list-disc list-inside">
                <li>Security incident records (incident type, severity, affected agents, timeline, resolution)</li>
                <li>Agent suspension and restoration records</li>
                <li>Webhook delivery logs including failure (dead-letter) records</li>
                <li>In-app notification records (type, severity, read status)</li>
              </ul>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-2">
              <h3 className="text-[14px] font-bold text-[#1F1F1F]">2.5 Audit Logs</h3>
              <ul className="text-[13px] text-[#555555] space-y-1 list-disc list-inside">
                <li>Causal provenance records tracing every agent action to its originating user, agent version, and policy rule</li>
                <li>Role-history change log (IAM role changes, timestamps, authorizing administrators)</li>
                <li>Report generation records (who generated, when, type)</li>
              </ul>
            </div>

            <div className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-2">
              <h3 className="text-[14px] font-bold text-[#1F1F1F]">2.6 Usage & Telemetry</h3>
              <ul className="text-[13px] text-[#555555] space-y-1 list-disc list-inside">
                <li>API request logs (endpoint, timestamp, HTTP status) — used for platform health monitoring</li>
                <li>Organization-level usage metrics (agent count, seat count, API call volume)</li>
                <li>Browser cookies for session management (see Section 6)</li>
              </ul>
              <p className="text-[12px] text-[#888888] mt-2">AGENTGUARD does not currently integrate third-party web analytics trackers (e.g., Google Analytics). The platform owner should update this if analytics are added.</p>
            </div>
          </div>
        </section>

        {/* 3. How We Use Data */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Eye className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">3. How We Use Your Data</h2>
          </div>
          <div className="space-y-3 text-[13px] text-[#555555]">
            {[
              ["Platform Operation", "To authenticate your identity, enforce your IAM role permissions, enforce tenant isolation across organizations, and deliver the AGENTGUARD governance platform features."],
              ["Security & Compliance", "To detect, record, and respond to security incidents involving AI agents; to generate governance audit trails; to enforce runtime policies."],
              ["Notifications", "To deliver in-app governance alerts, security warnings, approval requests, and system notifications scoped to your user account."],
              ["Email Delivery", "To deliver OTP verification codes via email at registration and password reset. The platform uses either Resend or SMTP, configured by the platform operator."],
              ["Reporting", "To generate compliance PDF and Excel reports from actual database records upon authorized user request."],
              ["Platform Health Monitoring", "To assess whether platform services (database, email, API) are operational and to surface accurate health status to Super Admin."],
            ].map(([title, desc]) => (
              <div key={title} className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex items-start gap-3">
                <CheckCircle2 className="w-4 h-4 text-[#2E9D50] mt-0.5 shrink-0" />
                <div>
                  <span className="font-bold text-[#1F1F1F] block">{title}</span>
                  <span className="text-[#666666]">{desc}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 4. Tenant Isolation */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Users className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">4. Multi-Tenant Data Isolation</h2>
          </div>
          <p className="text-[14px] text-[#555555] leading-relaxed">
            AGENTGUARD is a multi-tenant platform. Each organization&apos;s data — including users, AI agents, audit logs, notifications, and governance records — is strictly scoped to that organization and cannot be accessed by another tenant organization. The platform enforces this through SQL-level filtering on <code className="bg-[#F0F0ED] px-1.5 py-0.5 rounded text-[12px] font-mono">organization_id</code> across all data resources.
          </p>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            The <span className="font-mono font-bold text-[#8064C8]">SUPER_ADMIN</span> role is a platform-level identity that administers organization licenses and platform health. SUPER_ADMIN access is restricted to platform administration operations and does not expose individual organization users&apos; personal data beyond what is operationally necessary for platform administration.
          </p>
        </section>

        {/* 5. Third-Party Services */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <ExternalLink className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">5. Third-Party Services</h2>
          </div>
          <p className="text-[14px] text-[#555555] leading-relaxed">
            AGENTGUARD uses the following infrastructure services. Each processes data subject to their own terms and privacy policies:
          </p>
          <div className="space-y-3">
            {[
              {
                name: "Supabase",
                role: "Authentication and PostgreSQL database hosting",
                link: "https://supabase.com/privacy",
                data: "Authentication tokens, session data, database records. Supabase Auth is used for JWT token verification."
              },
              {
                name: "Render",
                role: "Backend API server hosting",
                link: "https://render.com/privacy",
                data: "API server deployment. Render hosts the FastAPI backend application."
              },
              {
                name: "Vercel",
                role: "Frontend Next.js application hosting",
                link: "https://vercel.com/legal/privacy-policy",
                data: "Frontend deployment and static page serving."
              },
              {
                name: "Resend (if configured)",
                role: "Transactional email delivery",
                link: "https://resend.com/legal/privacy-policy",
                data: "Email address and email content for OTP delivery and governance alert emails. Only used if the platform operator configures a Resend API key."
              },
            ].map((s) => (
              <div key={s.name} className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-1">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="font-bold text-[#1F1F1F] text-[14px]">{s.name}</span>
                  <span className="text-[11px] font-mono text-[#666666] bg-[#F0F0ED] px-2 py-0.5 rounded">{s.role}</span>
                </div>
                <p className="text-[13px] text-[#555555]">{s.data}</p>
                <a href={s.link} target="_blank" rel="noopener noreferrer" className="text-[12px] text-[#2E9D50] hover:underline flex items-center gap-1 w-fit">
                  Privacy Policy <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            ))}
          </div>
        </section>

        {/* 6. Cookies */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <FileText className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">6. Cookies & Session Storage</h2>
          </div>
          <div className="space-y-3 text-[13px] text-[#555555]">
            <p>AGENTGUARD uses the following browser storage mechanisms:</p>
            <div className="overflow-x-auto">
              <table className="w-full text-[12px] border border-[#E8E8E4] rounded-[8px] overflow-hidden">
                <thead className="bg-[#FCFCFA]">
                  <tr className="border-b border-[#E8E8E4]">
                    <th className="text-left px-3 py-2 font-bold text-[#1F1F1F]">Name</th>
                    <th className="text-left px-3 py-2 font-bold text-[#1F1F1F]">Type</th>
                    <th className="text-left px-3 py-2 font-bold text-[#1F1F1F]">Purpose</th>
                    <th className="text-left px-3 py-2 font-bold text-[#1F1F1F]">Expiry</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E8E8E4] bg-white">
                  <tr>
                    <td className="px-3 py-2 font-mono">agentguard_token</td>
                    <td className="px-3 py-2">Cookie</td>
                    <td className="px-3 py-2">JWT authentication session</td>
                    <td className="px-3 py-2">24 hours (SameSite=Lax)</td>
                  </tr>
                  <tr>
                    <td className="px-3 py-2 font-mono">agentguard_token</td>
                    <td className="px-3 py-2">localStorage</td>
                    <td className="px-3 py-2">JWT authentication session (browser fallback)</td>
                    <td className="px-3 py-2">Until explicit sign-out</td>
                  </tr>
                  <tr>
                    <td className="px-3 py-2 font-mono">agentguard_selected_org_id</td>
                    <td className="px-3 py-2">localStorage</td>
                    <td className="px-3 py-2">SUPER_ADMIN organization context selection</td>
                    <td className="px-3 py-2">Until sign-out or manual clear</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-[12px] text-[#888888]">No third-party tracking cookies are set by AGENTGUARD. If analytics or advertising integrations are added, this table must be updated.</p>
          </div>
        </section>

        {/* 7. Data Retention */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">7. Data Retention</h2>
          </div>
          <div className="space-y-2 text-[13px] text-[#555555]">
            <p>Data is retained for as long as your account and organization license is active, plus any legally required retention period thereafter. Specific retention details:</p>
            <ul className="space-y-1 list-disc list-inside">
              <li><strong>OTP codes:</strong> Expire after 10 minutes and are invalidated on use</li>
              <li><strong>Audit logs and Decision Black Box records:</strong> Retained for the duration of the organization&apos;s license as immutable governance records</li>
              <li><strong>Notifications:</strong> Retained until manually deleted by the user</li>
              <li><strong>Webhook dead-letter logs:</strong> Retained until explicitly cleared by an administrator</li>
              <li><strong>Account data:</strong> Retained for the life of the account; deleted upon request subject to legal obligations</li>
            </ul>
            <p className="text-[12px] text-[#888888] mt-2">The platform owner should define and document formal data retention periods before entering production, particularly for jurisdictions with specific retention requirements (e.g., GDPR Article 5(1)(e)).</p>
          </div>
        </section>

        {/* 8. Your Rights */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">8. Your Rights</h2>
          </div>
          <p className="text-[13px] text-[#555555]">Depending on your jurisdiction, you may have rights including:</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[13px]">
            {[
              ["Access", "Request a copy of your personal data held by AGENTGUARD"],
              ["Rectification", "Correct inaccurate personal data via your profile settings"],
              ["Erasure", "Request deletion of your personal data subject to legal obligations"],
              ["Portability", "Request your data in a machine-readable format"],
              ["Objection / Restriction", "Object to or restrict specific processing activities"],
              ["Withdraw Consent", "Where processing is based on consent, withdraw at any time"],
            ].map(([title, desc]) => (
              <div key={title} className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                <span className="font-bold text-[#1F1F1F] block text-[12px]">{title}</span>
                <span className="text-[#666666] text-[12px]">{desc}</span>
              </div>
            ))}
          </div>
          <p className="text-[13px] text-[#555555]">To exercise these rights, contact the platform administrator using the contact information provided during your organization onboarding. The platform owner must add a specific privacy email address here.</p>
        </section>

        {/* 9. Security */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">9. Security Practices</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            AGENTGUARD implements multiple technical security controls. See our <Link href="/security" className="text-[#2E9D50] font-bold hover:underline">Zero-Trust Security</Link> page for a detailed technical breakdown. Verified measures include:
          </p>
          <ul className="space-y-1.5 text-[13px] text-[#555555] list-disc list-inside">
            <li>JWT-based authentication with local secret verification and Supabase API fallback</li>
            <li>OTP verification for account creation with rate-limiting and cooldown</li>
            <li>Strict tenant isolation enforced at the SQL query layer (organization_id filtering)</li>
            <li>Role-based access control (RBAC) with 9-tier IAM hierarchy</li>
            <li>IDOR protection on all notification, agent, and resource endpoints</li>
            <li>No credential exposure in platform health API responses</li>
            <li>Session revocation checking on each authenticated request</li>
          </ul>
          <p className="text-[12px] text-[#888888]">No security system is 100% infallible. The platform owner should commission a penetration test and security audit before production launch and before making specific certification claims.</p>
        </section>

        {/* 10. Policy Changes */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">10. Changes to this Policy</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            We may update this Privacy Policy as the platform evolves. When we make material changes, we will update the &ldquo;Last reviewed&rdquo; date at the top and, where appropriate, notify organization administrators via in-app notification. Continued use of AGENTGUARD after changes constitutes acceptance of the revised policy.
          </p>
        </section>

        {/* 11. Contact */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Mail className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">11. Contact</h2>
          </div>
          <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] text-[13px] text-[#555555] space-y-2">
            <p>For privacy-related questions, data requests, or to exercise your rights, contact the platform operator.</p>
            <div className="p-3 bg-[#FFF4D9] border border-[#F59A23]/30 rounded-[8px] text-[12px] text-[#7A5000]">
              <strong>Action required for platform owner:</strong> Add your legal entity name, registered address, DPO contact email, and applicable jurisdiction information here before distributing this policy externally.
            </div>
          </div>
        </section>

      </div>

      {/* Footer */}
      <footer className="border-t border-[#E8E8E4] bg-[#FFFFFF] py-8 mt-8">
        <div className="max-w-[800px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[12px] text-[#666666]">
          <span>© {new Date().getFullYear()} AGENTGUARD. All rights reserved.</span>
          <div className="flex items-center gap-6">
            <Link href="/privacy" className="text-[#2E9D50] font-bold">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-[#1F1F1F] transition-colors">Terms of Service</Link>
            <Link href="/security" className="hover:text-[#1F1F1F] transition-colors">Zero-Trust Security</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
