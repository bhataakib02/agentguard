import type { Metadata } from "next";
import LegalDocShell, { DocSection, TocItem } from "@/components/legal/LegalDocShell";

export const metadata: Metadata = {
  title: "Terms of Service | AGENTGUARD",
  description:
    "Enterprise B2B Terms of Service for AGENTGUARD AI Agent Governance and Runtime Control Plane.",
  alternates: {
    canonical: "/terms",
  },
};

const TOC: TocItem[] = [
  { id: "agreement-acceptance", number: "1", title: "Agreement and Acceptance" },
  { id: "definitions", number: "2", title: "Definitions" },
  { id: "eligibility-authority", number: "3", title: "Eligibility and Authority" },
  { id: "account-registration", number: "4", title: "Account Registration and Security" },
  { id: "organization-workspace", number: "5", title: "Organization and Workspace Management" },
  { id: "subscription-billing", number: "6", title: "Subscription Plans and Billing" },
  { id: "trials-limitations", number: "7", title: "Free Trials and Service Limitations" },
  { id: "permitted-use", number: "8", title: "Permitted Use" },
  { id: "prohibited-activities", number: "9", title: "Prohibited Activities" },
  { id: "ai-agent-responsibilities", number: "10", title: "AI Agent and Automated System Responsibilities" },
  { id: "customer-responsibilities", number: "11", title: "Customer Responsibilities" },
  { id: "api-sdk-integrations", number: "12", title: "API, SDK and Integration Terms" },
  { id: "third-party-services", number: "13", title: "Third-Party Services" },
  { id: "data-ownership", number: "14", title: "Data Ownership" },
  { id: "customer-data-processing", number: "15", title: "Customer Data and Processing Rights" },
  { id: "intellectual-property", number: "16", title: "Intellectual Property Rights" },
  { id: "confidentiality", number: "17", title: "Confidentiality" },
  { id: "security-incident-reporting", number: "18", title: "Security and Incident Reporting" },
  { id: "availability-maintenance", number: "19", title: "Service Availability and Maintenance" },
  { id: "suspension-termination", number: "20", title: "Suspension and Termination" },
  { id: "data-export-deletion", number: "21", title: "Data Export and Deletion Following Termination" },
  { id: "warranties-disclaimers", number: "22", title: "Warranties and Disclaimers" },
  { id: "limitation-of-liability", number: "23", title: "Limitation of Liability" },
  { id: "indemnification", number: "24", title: "Indemnification" },
  { id: "dispute-resolution", number: "25", title: "Dispute Resolution" },
  { id: "governing-law", number: "26", title: "Governing Law and Jurisdiction" },
  { id: "changes-to-agreement", number: "27", title: "Changes to the Agreement" },
  { id: "contact-information", number: "28", title: "Contact Information" },
];

export default function TermsOfServicePage() {
  return (
    <LegalDocShell
      activeRoute="/terms"
      breadcrumbLabel="Terms of Service"
      title="Terms of Service"
      description="These Terms of Service govern enterprise access to and use of the AGENTGUARD AI Agent Governance and Runtime Control Plane."
      effectiveDate="[LEGAL REVIEW REQUIRED: Effective Date]"
      lastUpdated="November 27, 2026"
      version="2.0 (Draft — Pending Legal Counsel & Company Details)"
      toc={TOC}
    >
      <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] text-[#444444] leading-relaxed">
        <strong>Document Notice:</strong> This draft B2B Terms of Service requires review and approval by qualified legal counsel, including completion of governing law, liability caps, and registered company details, before being treated as a binding commercial agreement.
      </div>

      <DocSection id="agreement-acceptance" number="1" title="Agreement and Acceptance">
        <p>
          These Terms of Service (&ldquo;Agreement&rdquo;) constitute a legal agreement between{" "}
          <strong>[COMPANY INFORMATION REQUIRED: Legal Entity Name]</strong> (&ldquo;AGENTGUARD&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;) and the organization or entity accepting this Agreement (&ldquo;Customer&rdquo;, &ldquo;you&rdquo;). By creating an account, provisioning a workspace, or using the AGENTGUARD platform, you agree to be bound by this Agreement.
        </p>
      </DocSection>

      <DocSection id="definitions" number="2" title="Definitions">
        <ul className="list-disc pl-5 space-y-1.5">
          <li><strong>&ldquo;Platform&rdquo;</strong> means the AGENTGUARD web application, REST APIs, policy engine, risk scoring engine, approval workflows, and audit provenance tools.</li>
          <li><strong>&ldquo;Authorized User&rdquo;</strong> means an employee, contractor, or agent of Customer granted workspace credentials under Customer&apos;s IAM hierarchy.</li>
          <li><strong>&ldquo;Customer Data&rdquo;</strong> means all data, policies, agent metadata, logs, and reports submitted by or generated for Customer in its workspace.</li>
          <li><strong>&ldquo;Governed Agent&rdquo;</strong> means any autonomous software or AI agent registered, evaluated, or controlled by Customer using AGENTGUARD.</li>
        </ul>
      </DocSection>

      <DocSection id="eligibility-authority" number="3" title="Eligibility and Authority">
        <p>
          You represent that you are at least 18 years old and have full legal authority to bind the Customer organization to this Agreement. AGENTGUARD is intended strictly for business and enterprise use.
        </p>
      </DocSection>

      <DocSection id="account-registration" number="4" title="Account Registration and Security">
        <p>
          Registration requires a valid email address verified via a six-digit OTP. Each Authorized User must maintain confidential credentials and must not share accounts. Customer is responsible for all activity occurring under its Authorized Users&apos; accounts and must promptly revoke access for personnel who leave or no longer require access.
        </p>
      </DocSection>

      <DocSection id="organization-workspace" number="5" title="Organization and Workspace Management">
        <p>
          AGENTGUARD operates a multi-tenant architecture with organization-scoped workspaces. Customer workspace administrators (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ADMIN</code>) manage user roles, agent registrations, and policies within their tenant. Platform Super Administrators (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">SUPER_ADMIN</code>) are isolated to platform-level administration and licensing.
        </p>
      </DocSection>

      <DocSection id="subscription-billing" number="6" title="Subscription Plans and Billing">
        <p>
          Access to AGENTGUARD is governed by the Customer&apos;s assigned subscription tier (such as <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">STARTER</code>, <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">PROFESSIONAL</code>, or <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ENTERPRISE</code>) and associated seat and agent quotas.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Specify payment terms, invoicing, renewal, taxes, and refund policy.]</strong>
        </p>
      </DocSection>

      <DocSection id="trials-limitations" number="7" title="Free Trials and Service Limitations">
        <p>
          If Customer accesses AGENTGUARD under a trial or evaluation license, access may be subject to reduced agent quotas, user seat limits, or time-limited availability, and may be modified or terminated at any time without SLA commitments.
        </p>
      </DocSection>

      <DocSection id="permitted-use" number="8" title="Permitted Use">
        <p>
          Subject to compliance with this Agreement, AGENTGUARD grants Customer a non-exclusive, non-transferable, revocable right during the subscription term to access and use the Platform for internal enterprise AI agent governance, policy evaluation, human approval routing, security monitoring, and compliance reporting.
        </p>
      </DocSection>

      <DocSection id="prohibited-activities" number="9" title="Prohibited Activities">
        <p>Customer and its Authorized Users shall not:</p>
        <ul className="list-disc pl-5 space-y-1.5">
          <li>Attempt to access, probe, or interfere with another tenant organization&apos;s workspace or data;</li>
          <li>Bypass or attempt to defeat authentication, OTP rate limits, RBAC, or tenant-isolation controls;</li>
          <li>Reverse engineer, decompile, or copy the Platform&apos;s proprietary source code or algorithms;</li>
          <li>Use the Platform to govern AI agents engaged in unlawful, fraudulent, or abusive conduct; or</li>
          <li>Conduct unauthorized load testing, scraping, or denial-of-service activity against Platform endpoints.</li>
        </ul>
      </DocSection>

      <DocSection id="ai-agent-responsibilities" number="10" title="AI Agent and Automated System Responsibilities">
        <p>
          <strong>Human Oversight Requirement:</strong> AGENTGUARD provides runtime governance infrastructure, risk scoring, and deterministic policy evaluation (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ALLOW</code> / <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REVIEW</code> / <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REFUSE</code>). Automated outputs, risk scores, and enforcement decisions depend on policies configured by Customer and may require human oversight and judgment.
        </p>
        <p>
          Customer remains solely responsible for the design, deployment, prompts, downstream tool executions, regulatory compliance, and real-world actions of its Governed Agents.
        </p>
      </DocSection>

      <DocSection id="customer-responsibilities" number="11" title="Customer Responsibilities">
        <p>
          Customer is responsible for: (a) configuring appropriate policy thresholds, autonomy tiers, and approval workflows; (b) reviewing pending <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REVIEW</code> items in a timely manner; (c) maintaining accurate IAM role assignments; and (d) ensuring lawful collection and submission of Customer Data.
        </p>
      </DocSection>

      <DocSection id="api-sdk-integrations" number="12" title="API, SDK and Integration Terms">
        <p>
          API access requires valid JWT authentication and is subject to server-side role enforcement, pagination bounds (maximum 200 items per list request on supported endpoints), and webhook security controls. Customer must protect API credentials and capability tokens from unauthorized disclosure.
        </p>
      </DocSection>

      <DocSection id="third-party-services" number="13" title="Third-Party Services">
        <p>
          The Platform relies on third-party infrastructure providers (including Supabase, Render, Vercel, and transactional email providers such as Brevo or Resend) and may integrate with Customer-configured external webhooks or LLM APIs. AGENTGUARD is not responsible for outages or changes caused by third-party providers outside our reasonable control.
        </p>
      </DocSection>

      <DocSection id="data-ownership" number="14" title="Data Ownership">
        <p>
          As between the parties, Customer retains all right, title, and interest in and to Customer Data. AGENTGUARD claims no ownership over Customer Data, agent configurations, or generated compliance reports.
        </p>
      </DocSection>

      <DocSection id="customer-data-processing" number="15" title="Customer Data and Processing Rights">
        <p>
          Customer grants AGENTGUARD a limited license to host, process, transmit, and display Customer Data solely as necessary to provide, maintain, secure, and support the Platform in accordance with this Agreement and our Privacy Policy.
        </p>
      </DocSection>

      <DocSection id="intellectual-property" number="16" title="Intellectual Property Rights">
        <p>
          AGENTGUARD and its licensors retain all intellectual property rights in the Platform, user interfaces, software architecture, documentation, and trademarks. No rights are granted to Customer other than the limited right to use the Platform under this Agreement.
        </p>
      </DocSection>

      <DocSection id="confidentiality" number="17" title="Confidentiality">
        <p>
          Each party agrees to protect the other party&apos;s non-public business, technical, and security information with at least reasonable care and not to disclose it except to personnel or subprocessors bound by confidentiality obligations or as required by law.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Expand mutual confidentiality carve-outs and survival period.]</strong>
        </p>
      </DocSection>

      <DocSection id="security-incident-reporting" number="18" title="Security and Incident Reporting">
        <p>
          AGENTGUARD maintains technical controls documented on our Zero-Trust Security page. Customer agrees to promptly notify AGENTGUARD upon discovering any suspected compromise of workspace credentials, capability tokens, or Platform security.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Define breach notification timelines.]</strong>
        </p>
      </DocSection>

      <DocSection id="availability-maintenance" number="19" title="Service Availability and Maintenance">
        <p>
          The Platform is provided on an &ldquo;as available&rdquo; basis. We do not promise uninterrupted, error-free operation. Planned maintenance, security patches, or infrastructure updates may result in temporary service interruptions.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Add any commercial SLA or service credit schedule if offered.]</strong>
        </p>
      </DocSection>

      <DocSection id="suspension-termination" number="20" title="Suspension and Termination">
        <p>
          AGENTGUARD may suspend or terminate access if Customer materially breaches this Agreement, poses a security risk to the Platform or other tenants, or fails to pay applicable fees. Either party may terminate in accordance with the applicable subscription terms.
        </p>
      </DocSection>

      <DocSection id="data-export-deletion" number="21" title="Data Export and Deletion Following Termination">
        <p>
          Following termination, Customer&apos;s right to access the Platform ceases. Customer may request export of available governance and audit records prior to workspace deactivation.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Specify post-termination export window and deletion timeline.]</strong>
        </p>
      </DocSection>

      <DocSection id="warranties-disclaimers" number="22" title="Warranties and Disclaimers">
        <p>
          TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE PLATFORM IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR STATUTORY, INCLUDING IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT. AGENTGUARD DOES NOT WARRANT THAT GOVERNANCE CONTROLS WILL PREVENT ALL UNAUTHORIZED AGENT BEHAVIOR OR SECURITY INCIDENTS.
        </p>
      </DocSection>

      <DocSection id="limitation-of-liability" number="23" title="Limitation of Liability">
        <p>
          TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR LOSS OF PROFITS, REVENUE, OR DATA.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Insert aggregate liability cap (e.g., fees paid in prior 12 months) and statutory carve-outs.]</strong>
        </p>
      </DocSection>

      <DocSection id="indemnification" number="24" title="Indemnification">
        <p>
          <strong>[LEGAL REVIEW REQUIRED: Define mutual IP infringement indemnity by AGENTGUARD and Customer indemnity covering Governed Agents, Customer Data, and breach of Prohibited Activities.]</strong>
        </p>
      </DocSection>

      <DocSection id="dispute-resolution" number="25" title="Dispute Resolution">
        <p>
          Before initiating formal legal proceedings, the parties agree to attempt in good faith to resolve any dispute through written notice and executive negotiation.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Specify arbitration or litigation procedures.]</strong>
        </p>
      </DocSection>

      <DocSection id="governing-law" number="26" title="Governing Law and Jurisdiction">
        <p>
          <strong>[LEGAL REVIEW REQUIRED: Specify governing law, venue, and exclusive jurisdiction once operating entity domicile is confirmed.]</strong>
        </p>
      </DocSection>

      <DocSection id="changes-to-agreement" number="27" title="Changes to the Agreement">
        <p>
          We may revise this Agreement from time to time by posting an updated version and updating the &ldquo;Last Updated&rdquo; date. Material changes will be communicated to Customer administrators via email or in-app notification.
        </p>
      </DocSection>

      <DocSection id="contact-information" number="28" title="Contact Information">
        <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[13.5px]">
          <p><strong>Legal Entity:</strong> [COMPANY INFORMATION REQUIRED: Registered Legal Entity Name]</p>
          <p><strong>Registered Address:</strong> [COMPANY INFORMATION REQUIRED: Physical Business Address]</p>
          <p><strong>Legal Notices Email:</strong> [COMPANY INFORMATION REQUIRED: Legal Contact Email]</p>
        </div>
      </DocSection>
    </LegalDocShell>
  );
}
