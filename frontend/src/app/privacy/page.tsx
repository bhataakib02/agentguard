import type { Metadata } from "next";
import Link from "next/link";
import LegalDocShell, { DocSection, TocItem } from "@/components/legal/LegalDocShell";

export const metadata: Metadata = {
  title: "Privacy Policy | AGENTGUARD",
  description:
    "Enterprise Privacy Policy for AGENTGUARD: data collection, AI agent runtime telemetry, subprocessors, retention, security, and privacy rights.",
  alternates: {
    canonical: "/privacy",
  },
};

const TOC: TocItem[] = [
  { id: "introduction-scope", number: "1", title: "Introduction and Scope" },
  { id: "definitions", number: "2", title: "Definitions and Interpretation" },
  { id: "information-we-collect", number: "3", title: "Information We Collect and Do Not Collect" },
  { id: "personal-account-info", number: "4", title: "Personal and Account Information" },
  { id: "agent-runtime-usage", number: "5", title: "AI Agent, Runtime and Usage Data" },
  { id: "technical-logs-telemetry", number: "6", title: "Technical Information, Logs and Telemetry" },
  { id: "cookies-storage", number: "7", title: "Cookies and Similar Technologies" },
  { id: "how-we-use-info", number: "8", title: "How We Use Personal Information" },
  { id: "legal-bases", number: "9", title: "Legal Bases for Processing" },
  { id: "ai-automated-decisions", number: "10", title: "AI Processing and Automated Decision-Making" },
  { id: "ai-third-party-integrations", number: "11", title: "AI Model and Third-Party Integrations" },
  { id: "data-sharing-subprocessors", number: "12", title: "Data Sharing and Subprocessors" },
  { id: "core-infrastructure-providers", number: "13", title: "Supabase, Render, Vercel and Email Providers" },
  { id: "storage-hosting-locations", number: "14", title: "Data Storage and Hosting Locations" },
  { id: "international-transfers", number: "15", title: "International Data Transfers" },
  { id: "retention-deletion", number: "16", title: "Data Retention and Deletion" },
  { id: "data-security", number: "17", title: "Data Security Measures" },
  { id: "access-correction-deletion", number: "18", title: "Access, Correction and Deletion Rights" },
  { id: "jurisdictional-rights", number: "19", title: "User and Jurisdictional Privacy Rights" },
  { id: "childrens-privacy", number: "20", title: "Children's Privacy" },
  { id: "business-transfers", number: "21", title: "Business Transfers" },
  { id: "policy-changes", number: "22", title: "Changes to This Privacy Policy" },
  { id: "contact-enquiries", number: "23", title: "Contact and Privacy Enquiries" },
];

export default function PrivacyPolicyPage() {
  return (
    <LegalDocShell
      activeRoute="/privacy"
      breadcrumbLabel="Privacy Policy"
      title="Privacy Policy"
      description="This Privacy Policy describes how AGENTGUARD collects, processes, stores, and protects information in connection with the AGENTGUARD AI Agent Governance and Runtime Control Plane."
      effectiveDate="[LEGAL REVIEW REQUIRED: Effective Date]"
      lastUpdated="November 27, 2026"
      version="2.0 (Draft — Pending Legal Counsel & Company Details)"
      toc={TOC}
    >
      <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] text-[#444444] leading-relaxed">
        <strong>Document Notice:</strong> This draft Privacy Policy reflects the verified technical architecture of AGENTGUARD and requires review and approval by qualified legal counsel, along with insertion of registered entity details, before being treated as binding legal documentation.
      </div>

      <DocSection id="introduction-scope" number="1" title="Introduction and Scope">
        <p>
          This Privacy Policy applies to the AGENTGUARD web application, APIs, and enterprise governance control plane operated by{" "}
          <strong>[COMPANY INFORMATION REQUIRED: Legal Entity Name]</strong> (&ldquo;AGENTGUARD&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;).
        </p>
        <p>
          It governs information processed when organizations (&ldquo;Customers&rdquo;) and their authorized personnel (&ldquo;Users&rdquo;) register accounts, authenticate, configure policies, monitor autonomous AI agents, review approvals, or interact with our public documentation.
        </p>
      </DocSection>

      <DocSection id="definitions" number="2" title="Definitions and Interpretation">
        <ul className="list-disc pl-5 space-y-2">
          <li><strong>&ldquo;Customer&rdquo;</strong> means the organization or business entity that provisions a workspace or license in AGENTGUARD.</li>
          <li><strong>&ldquo;User&rdquo;</strong> means an individual authorized by a Customer (or a Platform Super Administrator) to access AGENTGUARD.</li>
          <li><strong>&ldquo;Customer Data&rdquo;</strong> means all data, agent configurations, policy rules, approval records, and audit logs submitted to or generated within a Customer&apos;s isolated tenant workspace.</li>
          <li><strong>&ldquo;Personal Information&rdquo;</strong> means any information relating to an identified or identifiable natural person.</li>
          <li><strong>&ldquo;OTP&rdquo;</strong> means a six-digit one-time passcode used for email verification, passwordless sign-in, or password recovery.</li>
        </ul>
      </DocSection>

      <DocSection id="information-we-collect" number="3" title="Information We Collect and Do Not Collect">
        <p>AGENTGUARD collects only the information required to authenticate users, isolate tenant workspaces, govern AI agents, and maintain security and audit logs.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          <div className="p-4 border border-[#E8E8E4] rounded-[8px] bg-[#FCFCFA]">
            <h3 className="font-bold text-[#141414] text-[13.5px] mb-2">What We Collect</h3>
            <ul className="list-disc pl-4 space-y-1 text-[13px]">
              <li>Account profile and authentication records (name, email, hashed credentials, IAM role)</li>
              <li>AI agent identity, capability tokens, policies, and risk scores</li>
              <li>Governance decisions, human approvals, security incidents, and audit provenance</li>
              <li>Session tokens, IP addresses on auth/OTP requests, and API health metrics</li>
            </ul>
          </div>
          <div className="p-4 border border-[#E8E8E4] rounded-[8px] bg-[#FCFCFA]">
            <h3 className="font-bold text-[#141414] text-[13.5px] mb-2">What We Do Not Collect</h3>
            <ul className="list-disc pl-4 space-y-1 text-[13px]">
              <li>We do not sell Personal Information to third parties</li>
              <li>We do not embed third-party advertising trackers or cross-site ad cookies</li>
              <li>We do not store plaintext passwords or plaintext OTP codes in database records</li>
              <li>We do not expose API keys or database credentials in API responses or logs</li>
            </ul>
          </div>
        </div>
      </DocSection>

      <DocSection id="personal-account-info" number="4" title="Personal and Account Information">
        <p>When you register or are provisioned in an organization workspace, we collect:</p>
        <ul className="list-disc pl-5 space-y-1.5">
          <li><strong>Identity &amp; Contact:</strong> Full name and normalized email address.</li>
          <li><strong>Credentials:</strong> Password hashes (plaintext passwords are never persisted; during registration OTP verification, an ephemeral AES-256-GCM encrypted payload is held temporarily in the challenge metadata and scrubbed immediately upon verification).</li>
          <li><strong>OTP Verification Challenges:</strong> Keyed HMAC-SHA256 digests of six-digit OTP codes, purpose binding (registration, passwordless login, or password reset), attempt counters, 10-minute expiration timestamps, and 120-second resend cooldown timestamps.</li>
          <li><strong>Organization &amp; IAM Metadata:</strong> Organization identifier (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">org_id</code>), department, IAM role (e.g., <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">USER</code>, <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">MANAGER</code>, <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ADMIN</code>), account status (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ACTIVE</code> / <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">SUSPENDED</code>), and last login timestamp.</li>
        </ul>
      </DocSection>

      <DocSection id="agent-runtime-usage" number="5" title="AI Agent, Runtime and Usage Data">
        <p>Within each Customer workspace, AGENTGUARD processes operational governance data including:</p>
        <ul className="list-disc pl-5 space-y-1.5">
          <li><strong>Agent Passports:</strong> Agent codes, names, model identifiers, autonomy tiers, daily budgets, owners, and operational status.</li>
          <li><strong>Policy &amp; Decision Records:</strong> Policy rules, deterministic evaluation outcomes (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ALLOW</code>, <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REVIEW</code>, <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REFUSE</code>), risk scores (0&ndash;100), and Decision Black Box entries.</li>
          <li><strong>Human Approvals &amp; Security Incidents:</strong> Approval requests, reviewer decisions, circuit-breaker (kill switch) actions, security incidents, and in-app notifications.</li>
        </ul>
      </DocSection>

      <DocSection id="technical-logs-telemetry" number="6" title="Technical Information, Logs and Telemetry">
        <p>Our backend API and infrastructure record operational logs necessary for security and troubleshooting:</p>
        <ul className="list-disc pl-5 space-y-1.5">
          <li><strong>IP Addresses:</strong> Captured from request headers (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">X-Forwarded-For</code> or client socket) on session creation, OTP rate limiting, and security audit logs.</li>
          <li><strong>Audit &amp; Delivery Logs:</strong> Authentication events, role-history changes, webhook delivery attempts, and email dispatch correlation IDs/HTTP status codes (OTP codes, passwords, and API keys are excluded from logs).</li>
        </ul>
      </DocSection>

      <DocSection id="cookies-storage" number="7" title="Cookies and Similar Technologies">
        <p>AGENTGUARD uses strictly necessary browser cookies and <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">localStorage</code> entries for authentication and workspace state:</p>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] border border-[#E8E8E4] border-collapse">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4]">
                <th className="text-left px-3 py-2 font-bold text-[#141414]">Key</th>
                <th className="text-left px-3 py-2 font-bold text-[#141414]">Mechanism</th>
                <th className="text-left px-3 py-2 font-bold text-[#141414]">Purpose</th>
                <th className="text-left px-3 py-2 font-bold text-[#141414]">Lifetime</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              <tr>
                <td className="px-3 py-2 font-mono text-[12px]">agentguard_token</td>
                <td className="px-3 py-2">Cookie (<code className="text-[12px]">SameSite=Lax</code>)</td>
                <td className="px-3 py-2">JWT session authentication</td>
                <td className="px-3 py-2">24 hours</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[12px]">agentguard_token</td>
                <td className="px-3 py-2">localStorage</td>
                <td className="px-3 py-2">API Bearer token attachment</td>
                <td className="px-3 py-2">Until sign-out or clearance</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[12px]">agentguard_selected_org_id</td>
                <td className="px-3 py-2">localStorage</td>
                <td className="px-3 py-2">Super Admin tenant context selector</td>
                <td className="px-3 py-2">Until cleared</td>
              </tr>
            </tbody>
          </table>
        </div>
      </DocSection>

      <DocSection id="how-we-use-info" number="8" title="How We Use Personal Information">
        <ul className="list-disc pl-5 space-y-1.5">
          <li>Authenticate users, verify email ownership via OTP, and enforce role-based access control.</li>
          <li>Maintain strict organization-level tenant isolation across multi-tenant workspaces.</li>
          <li>Evaluate AI agent runtime policies, compute risk scores, and route high-risk operations for human approval.</li>
          <li>Deliver transactional OTP emails and in-app security or governance notifications.</li>
          <li>Detect, investigate, and prevent abuse, rate-limit violations, unauthorized access, and security incidents.</li>
        </ul>
      </DocSection>

      <DocSection id="legal-bases" number="9" title="Legal Bases for Processing">
        <p>
          Where data protection laws require a legal basis (such as the GDPR or UK GDPR), processing is based on: (a) performance of a contract with the Customer; (b) legitimate interests in platform security, fraud prevention, and AI governance; (c) compliance with legal obligations; or (d) user consent where explicitly obtained.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Confirm applicable legal bases for target jurisdictions.]</strong>
        </p>
      </DocSection>

      <DocSection id="ai-automated-decisions" number="10" title="AI Processing and Automated Decision-Making">
        <p>
          AGENTGUARD evaluates AI agent actions using deterministic policy rules and risk scoring models (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ALLOW</code>, <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REVIEW</code>, <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REFUSE</code>). Operations classified as <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">REVIEW</code> are routed to human approvers (<code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">MANAGER</code> / <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">ADMIN</code>). AGENTGUARD does not perform automated profiling of human end-users for advertising, credit, or employment decisions.
        </p>
      </DocSection>

      <DocSection id="ai-third-party-integrations" number="11" title="AI Model and Third-Party Integrations">
        <p>
          Where a Customer or operator configures optional external LLM providers (such as OpenAI, Anthropic, or Google Gemini) for assistant or intelligence features, prompts and relevant context are transmitted to the configured provider. Customers are responsible for reviewing the privacy terms of any third-party AI providers they enable.
        </p>
      </DocSection>

      <DocSection id="data-sharing-subprocessors" number="12" title="Data Sharing and Subprocessors">
        <p>
          We do not sell Personal Information. Information is shared only with infrastructure subprocessors required to operate AGENTGUARD, with Customer workspace administrators as permitted by IAM roles, or when required by valid legal process.
        </p>
      </DocSection>

      <DocSection id="core-infrastructure-providers" number="13" title="Supabase, Render, Vercel and Email Providers">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] border border-[#E8E8E4] border-collapse">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4]">
                <th className="text-left px-3 py-2 font-bold text-[#141414]">Provider</th>
                <th className="text-left px-3 py-2 font-bold text-[#141414]">Role</th>
                <th className="text-left px-3 py-2 font-bold text-[#141414]">Data Processed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              <tr>
                <td className="px-3 py-2 font-bold">Supabase</td>
                <td className="px-3 py-2">PostgreSQL Database &amp; Auth</td>
                <td className="px-3 py-2">Authentication identities, JWT verification, tenant and audit records</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold">Render</td>
                <td className="px-3 py-2">Backend API &amp; Worker Hosting</td>
                <td className="px-3 py-2">FastAPI application traffic, API logs, Redis-backed background tasks</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold">Vercel</td>
                <td className="px-3 py-2">Frontend Application Hosting</td>
                <td className="px-3 py-2">Next.js web application serving and edge HTTP request routing</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold">Brevo / Resend / SMTP</td>
                <td className="px-3 py-2">Transactional Email Delivery</td>
                <td className="px-3 py-2">Recipient email address and OTP/notification email content (based on active <code className="text-[12px]">EMAIL_PROVIDER</code>)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </DocSection>

      <DocSection id="storage-hosting-locations" number="14" title="Data Storage and Hosting Locations">
        <p>
          Application data is stored in PostgreSQL hosted via Supabase, with backend services configured for Render (currently configured in <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">singapore</code> in deployment manifests) and frontend delivery via Vercel&apos;s global edge network.{" "}
          <strong>[COMPANY INFORMATION REQUIRED: Confirm exact production Supabase database region and object storage region.]</strong>
        </p>
      </DocSection>

      <DocSection id="international-transfers" number="15" title="International Data Transfers">
        <p>
          Because our hosting and email subprocessors operate globally, Personal Information may be transferred to and processed in countries other than your country of residence.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Specify transfer safeguards such as Standard Contractual Clauses (SCCs) or adequacy mechanisms where applicable.]</strong>
        </p>
      </DocSection>

      <DocSection id="retention-deletion" number="16" title="Data Retention and Deletion">
        <p>AGENTGUARD configuration includes retention parameters for operational tables (with defaults in backend configuration of 365 days for audit logs, 90 days for telemetry, and 7 days for expired sessions), though automated scheduled purge jobs are not yet uniformly enforced across all tables:</p>
        <ul className="list-disc pl-5 space-y-1.5">
          <li><strong>OTP Challenges:</strong> Expire 10 minutes after issuance and are invalidated upon consumption or superseding issuance.</li>
          <li><strong>Sessions:</strong> Expire after 24 hours or upon explicit revocation.</li>
          <li><strong>Notifications:</strong> Retained until dismissed/deleted by the user.</li>
          <li><strong>Audit Logs &amp; Governance Records:</strong> Retained as part of the organization&apos;s governance history; automated deletion schedules require further implementation and Customer policy alignment.</li>
        </ul>
      </DocSection>

      <DocSection id="data-security" number="17" title="Data Security Measures">
        <p>
          Technical controls implemented in the codebase include JWT signature verification, session revocation checks, 9-tier RBAC, SQL-level <code className="text-[12.5px] bg-[#F2F2EE] px-1.5 py-0.5 rounded">org_id</code> tenant isolation, parameterized SQLAlchemy queries, HMAC-SHA256 OTP storage, and AES-256-GCM ephemeral secret encryption during registration. Full technical details and verification status are published on our{" "}
          <Link href="/security" className="text-[#1E6B36] font-bold hover:underline">
            Zero-Trust Security
          </Link>{" "}
          page.
        </p>
      </DocSection>

      <DocSection id="access-correction-deletion" number="18" title="Access, Correction and Deletion Rights">
        <p>
          Users may view and update profile details in the workspace Profile settings. Requests for full account deletion, data export, or correction of administrative records should be directed to your Customer organization administrator or our privacy contact below.
        </p>
      </DocSection>

      <DocSection id="jurisdictional-rights" number="19" title="User and Jurisdictional Privacy Rights">
        <p>
          Depending on applicable law (such as GDPR, UK GDPR, or CCPA/CPRA), individuals may have rights to access, rectify, erase, restrict, or object to processing of their Personal Information, as well as data portability and the right to lodge a complaint with a supervisory authority.{" "}
          <strong>[LEGAL REVIEW REQUIRED: Tailor statutory disclosures for target jurisdictions.]</strong>
        </p>
      </DocSection>

      <DocSection id="childrens-privacy" number="20" title="Children's Privacy">
        <p>
          AGENTGUARD is an enterprise B2B software platform and is not directed to individuals under 18 years of age (or the applicable age of digital consent). We do not knowingly collect Personal Information from children.
        </p>
      </DocSection>

      <DocSection id="business-transfers" number="21" title="Business Transfers">
        <p>
          In the event of a merger, acquisition, reorganization, or sale of assets, Personal Information may be transferred as part of the transaction, subject to continued protection consistent with this Privacy Policy or prior notice to affected Customers.
        </p>
      </DocSection>

      <DocSection id="policy-changes" number="22" title="Changes to This Privacy Policy">
        <p>
          We may update this Privacy Policy to reflect platform changes or legal requirements. Material updates will be indicated by updating the &ldquo;Last Updated&rdquo; date and version number at the top of this page and, where appropriate, via in-app notification.
        </p>
      </DocSection>

      <DocSection id="contact-enquiries" number="23" title="Contact and Privacy Enquiries">
        <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[13.5px]">
          <p><strong>Data Controller / Operator:</strong> [COMPANY INFORMATION REQUIRED: Registered Legal Entity Name]</p>
          <p><strong>Registered Address:</strong> [COMPANY INFORMATION REQUIRED: Physical Business Address]</p>
          <p><strong>Privacy Contact / DPO:</strong> [COMPANY INFORMATION REQUIRED: Privacy Contact Email]</p>
        </div>
      </DocSection>
    </LegalDocShell>
  );
}
