"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { FileText, Shield, AlertTriangle, CheckCircle2, Ban, Zap, Scale } from "lucide-react";

export default function TermsOfServicePage() {
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
              <FileText className="w-5 h-5 text-[#237A3C]" />
            </div>
            <div>
              <h1 className="text-[28px] sm:text-[34px] font-bold text-[#1F1F1F] tracking-tight leading-tight">Terms of Service</h1>
              <p className="text-[13px] text-[#666666] mt-0.5">Effective date: November 2025 · Last reviewed: November 2025</p>
            </div>
          </div>
          <p className="text-[15px] text-[#555555] leading-relaxed">
            These Terms of Service govern your access to and use of AGENTGUARD, an enterprise AI Agent Governance and Runtime Control Plane. By accessing or using AGENTGUARD, you agree to be bound by these terms.
          </p>
          <div className="mt-5 p-4 bg-[#FFF4D9] border border-[#F59A23]/30 rounded-[10px] flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-[#B76E00] mt-0.5 shrink-0" />
            <p className="text-[12px] text-[#7A5000] leading-relaxed">
              <strong>Legal Notice:</strong> These terms require review and supplementation by qualified legal counsel before production use. The platform owner must add their registered legal entity name, jurisdiction, governing law, dispute resolution mechanism, and liability caps. Items marked [LEGAL REVIEW REQUIRED] must be completed before this document is legally binding.
            </p>
          </div>
        </div>
      </section>

      {/* Content */}
      <div className="max-w-[800px] mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">

        {/* 1. Service Description */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Shield className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">1. Service Description</h2>
          </div>
          <p className="text-[14px] text-[#555555] leading-relaxed">
            AGENTGUARD is a Software-as-a-Service platform that provides enterprise-grade governance infrastructure for autonomous AI agents. The platform includes:
          </p>
          <ul className="space-y-1.5 text-[13px] text-[#555555] list-disc list-inside">
            <li><strong>Agent Identity Management:</strong> Digital passports, capability tokens, and permission matrices for AI agents</li>
            <li><strong>Runtime Policy Engine:</strong> Deterministic rule evaluation for ALLOW / REVIEW / REFUSE governance decisions</li>
            <li><strong>Risk Intelligence:</strong> Dynamic risk scoring (0–100) based on agent behavior and payload analysis</li>
            <li><strong>Human-in-the-Loop Approvals:</strong> Approval workflow routing for high-risk agent operations</li>
            <li><strong>Security Incident Management:</strong> Incident creation, tracking, resolution, and notification</li>
            <li><strong>Circuit Breaker (Kill Switch):</strong> Immediate agent suspension capability</li>
            <li><strong>Decision Black Box:</strong> Immutable governance audit records</li>
            <li><strong>Causal Audit Provenance:</strong> Full forensic tracing of agent actions</li>
            <li><strong>Multi-Tenant Organization Management:</strong> Isolated workspaces per organization with license controls</li>
            <li><strong>Notification System:</strong> In-app governance alerts, security notifications, and event-driven messaging</li>
            <li><strong>Reporting:</strong> PDF, Excel, and CSV compliance reports from live database records</li>
          </ul>
        </section>

        {/* 2. Account Responsibility */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">2. Account Registration & Responsibility</h2>
          </div>
          <div className="space-y-3 text-[13px] text-[#555555]">
            <p>To use AGENTGUARD, you must register with a valid email address and complete OTP email verification. You agree that:</p>
            <ul className="space-y-1.5 list-disc list-inside">
              <li>You will provide accurate registration information and keep it up to date</li>
              <li>You are responsible for maintaining the security of your account credentials</li>
              <li>You will immediately notify your organization administrator if you suspect unauthorized access</li>
              <li>You are responsible for all actions taken under your account, including those of AI agents operating under your governance oversight</li>
              <li>Sharing account credentials with other individuals is prohibited</li>
              <li>Your organization administrator is responsible for managing IAM roles and removing access when users leave</li>
            </ul>
          </div>
        </section>

        {/* 3. Authorized Use */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">3. Authorized Use</h2>
          </div>
          <p className="text-[13px] text-[#555555]">AGENTGUARD is provided for legitimate enterprise AI governance purposes. Authorized use includes:</p>
          <ul className="space-y-1.5 text-[13px] text-[#555555] list-disc list-inside">
            <li>Governing, monitoring, and auditing autonomous AI agent operations within your organization</li>
            <li>Configuring runtime policies and risk thresholds for AI agent behavior</li>
            <li>Reviewing and approving or refusing AI agent operations requiring human oversight</li>
            <li>Generating compliance and audit reports from your organization&apos;s governance records</li>
            <li>Managing user IAM roles within your authorized organization scope</li>
            <li>Administering platform organizations, licenses, and billing (SUPER_ADMIN only)</li>
          </ul>
        </section>

        {/* 4. AI Agent Usage */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Zap className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">4. AI Agent Usage & Governance Responsibility</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            AGENTGUARD provides a governance control plane. The underlying AI agents that you govern through AGENTGUARD are your responsibility. You acknowledge that:
          </p>
          <ul className="space-y-1.5 text-[13px] text-[#555555] list-disc list-inside">
            <li>You are responsible for the AI agents you register, configure, and govern through AGENTGUARD</li>
            <li>AGENTGUARD provides governance infrastructure — it does not independently operate, train, or deploy AI models</li>
            <li>You are responsible for ensuring your AI agent operations comply with applicable laws and regulations in your jurisdiction</li>
            <li>Governance decisions (ALLOW / REVIEW / REFUSE) are based on the policies and thresholds you configure — you are responsible for configuring appropriate controls</li>
            <li>Human approvers designated in your organization are responsible for the approval decisions they make</li>
            <li>The circuit breaker (kill switch) must be used responsibly; misuse to disrupt legitimate operations is prohibited</li>
          </ul>
        </section>

        {/* 5. Prohibited Activity */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#FDECEC] flex items-center justify-center">
              <Ban className="w-4 h-4 text-[#C62828]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">5. Prohibited Activity</h2>
          </div>
          <p className="text-[13px] text-[#555555]">The following activities are strictly prohibited:</p>
          <div className="space-y-2">
            {[
              "Attempting to access another tenant organization&apos;s data, users, agents, or governance records",
              "Attempting to bypass, circumvent, or defeat authentication, authorization, or tenant isolation controls",
              "Using AGENTGUARD to govern AI agents engaged in illegal, harmful, fraudulent, or abusive activities",
              "Submitting false registration information or impersonating another user or organization",
              "Reverse engineering, decompiling, or attempting to extract AGENTGUARD source code or proprietary algorithms",
              "Using the API beyond your licensed rate limits or in ways designed to degrade platform performance",
              "Storing or processing data through AGENTGUARD that violates applicable law, including unlawful personal data",
              "Attempting to exploit security vulnerabilities in the platform (responsible disclosure is encouraged — contact the platform operator)",
              "Using AGENTGUARD platform features to process personal data of minors without required consents and safeguards",
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-2.5 p-3 bg-[#FDECEC]/30 border border-[#E53935]/20 rounded-[8px]">
                <Ban className="w-3.5 h-3.5 text-[#E53935] mt-0.5 shrink-0" />
                <span className="text-[13px] text-[#555555]" dangerouslySetInnerHTML={{ __html: item }} />
              </div>
            ))}
          </div>
        </section>

        {/* 6. API Usage */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">6. API Usage</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            AGENTGUARD exposes a RESTful API for integration with your AI agent systems. API access requires valid JWT authentication. All API requests are subject to:
          </p>
          <ul className="space-y-1.5 text-[13px] text-[#555555] list-disc list-inside">
            <li>Authentication via JWT token on every request</li>
            <li>Role-based authorization enforced server-side on every endpoint</li>
            <li>Rate limiting and pagination bounds (default: 50 notifications per request, max 200)</li>
            <li>Tenant isolation — API responses are automatically scoped to the authenticated user&apos;s organization</li>
          </ul>
          <p className="text-[13px] text-[#555555]">API keys and tokens must be kept confidential and must not be committed to public version control repositories.</p>
        </section>

        {/* 7. Third-Party Services */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">7. Third-Party Services</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            AGENTGUARD relies on third-party infrastructure providers including Supabase (database and authentication), Render (backend hosting), Vercel (frontend hosting), and optionally Resend (email delivery). Your use of AGENTGUARD is also subject to the applicable terms of service of these providers. We are not responsible for outages, data loss, or service changes caused by our infrastructure providers.
          </p>
        </section>

        {/* 8. Service Availability */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">8. Service Availability & Limitations</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            AGENTGUARD is provided &ldquo;as available.&rdquo; We do not guarantee uninterrupted, error-free service. We may perform maintenance, updates, or infrastructure changes that temporarily affect availability. The platform health dashboard (accessible to SUPER_ADMIN) provides real-time status of all platform services.
          </p>
          <p className="text-[13px] text-[#555555]">
            [LEGAL REVIEW REQUIRED: Define specific SLA uptime commitments, maintenance windows, and credits for downtime if applicable to your business model.]
          </p>
        </section>

        {/* 9. Intellectual Property */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">9. Intellectual Property</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            AGENTGUARD, its platform software, design system, governance algorithms, runtime policy engine, and all associated intellectual property are owned by the platform operator. You are granted a limited, non-exclusive, non-transferable license to use the platform in accordance with these Terms during your subscription period.
          </p>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            Your organization&apos;s data — including agent records, audit logs, governance decisions, and user data — remains your property. By using AGENTGUARD, you grant us the right to process this data solely to deliver the platform services.
          </p>
        </section>

        {/* 10. Suspension & Termination */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">10. Suspension & Termination</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            We reserve the right to suspend or terminate access to AGENTGUARD for:
          </p>
          <ul className="space-y-1.5 text-[13px] text-[#555555] list-disc list-inside">
            <li>Violation of these Terms of Service</li>
            <li>Non-payment of applicable subscription fees</li>
            <li>Illegal or harmful use of the platform</li>
            <li>Security breach or compromise of the platform</li>
            <li>Exceeding license quotas after reasonable notice</li>
          </ul>
          <p className="text-[13px] text-[#555555] mt-2">
            Upon termination, your access to the platform ceases. Data export requests will be honored for a reasonable period following termination subject to applicable law. [LEGAL REVIEW REQUIRED: Define the specific data export and deletion window, e.g., 30 days.]
          </p>
        </section>

        {/* 11. Limitation of Liability */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <div className="w-8 h-8 rounded-[6px] bg-[#EAF7EE] flex items-center justify-center">
              <Scale className="w-4 h-4 text-[#237A3C]" />
            </div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">11. Limitation of Liability & Disclaimer</h2>
          </div>
          <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] space-y-3 text-[13px] text-[#555555]">
            <p>
              AGENTGUARD IS PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT.
            </p>
            <p>
              AGENTGUARD IS A GOVERNANCE TOOL — IT DOES NOT GUARANTEE THAT AI AGENTS GOVERNED THROUGH THE PLATFORM WILL NEVER CAUSE HARM. YOU REMAIN RESPONSIBLE FOR YOUR AI AGENTS AND THEIR ACTIONS.
            </p>
            <p>
              [LEGAL REVIEW REQUIRED: Add jurisdiction-specific liability cap, e.g., &ldquo;In no event shall our total liability exceed the fees paid in the 12 months preceding the claim.&rdquo; Add warranty disclaimer language appropriate for your jurisdiction.]
            </p>
          </div>
        </section>

        {/* 12. User Responsibility */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">12. User Responsibility & Indemnification</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            You agree to indemnify and hold harmless AGENTGUARD and its operators from any claims, damages, or expenses arising from: (a) your violation of these Terms; (b) your use of AGENTGUARD in a manner that harms a third party; (c) the actions of AI agents you govern through the platform; or (d) your breach of applicable law.
          </p>
          <p className="text-[13px] text-[#555555]">[LEGAL REVIEW REQUIRED: Review indemnification scope for your jurisdiction and business structure.]</p>
        </section>

        {/* 13. Changes */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">13. Changes to These Terms</h2>
          </div>
          <p className="text-[13px] text-[#555555] leading-relaxed">
            We may update these Terms as the platform evolves. Material changes will be communicated to organization administrators via in-app notification at least 14 days before they take effect. Continued use of AGENTGUARD after the effective date constitutes acceptance of the revised Terms.
          </p>
        </section>

        {/* 14. Governing Law */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">14. Governing Law & Dispute Resolution</h2>
          </div>
          <div className="p-4 bg-[#FFF4D9] border border-[#F59A23]/30 rounded-[10px] text-[13px] text-[#7A5000]">
            <p className="font-bold mb-2">[LEGAL REVIEW REQUIRED]</p>
            <p>This section must be completed by qualified legal counsel. It must specify:</p>
            <ul className="mt-2 space-y-1 list-disc list-inside">
              <li>The governing jurisdiction and applicable law (e.g., &ldquo;laws of the State of [X], USA&rdquo; or &ldquo;laws of [Country]&rdquo;)</li>
              <li>The dispute resolution mechanism (e.g., binding arbitration, court jurisdiction)</li>
              <li>Venue and forum for disputes</li>
              <li>Class action waiver (if applicable in your jurisdiction)</li>
            </ul>
          </div>
        </section>

        {/* 15. Contact */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#E8E8E4]">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">15. Contact Information</h2>
          </div>
          <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] text-[13px] text-[#555555] space-y-2">
            <p>For questions about these Terms of Service, contact the platform operator.</p>
            <div className="p-3 bg-[#FFF4D9] border border-[#F59A23]/30 rounded-[8px] text-[12px] text-[#7A5000]">
              <strong>Action required for platform owner:</strong> Add your legal entity name, registered business address, and legal/compliance contact email here.
            </div>
          </div>
        </section>

      </div>

      {/* Footer */}
      <footer className="border-t border-[#E8E8E4] bg-[#FFFFFF] py-8 mt-8">
        <div className="max-w-[800px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[12px] text-[#666666]">
          <span>© {new Date().getFullYear()} AGENTGUARD. All rights reserved.</span>
          <div className="flex items-center gap-6">
            <Link href="/privacy" className="hover:text-[#1F1F1F] transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="text-[#2E9D50] font-bold">Terms of Service</Link>
            <Link href="/security" className="hover:text-[#1F1F1F] transition-colors">Zero-Trust Security</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
