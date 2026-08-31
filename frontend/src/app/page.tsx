"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Shield,
  Bot,
  Lock,
  Activity,
  UserCheck,
  Zap,
  ArrowRight,
  CheckCircle2,
  FileText,
  Building2,
  Cpu,
  Layers,
  FileSpreadsheet,
  AlertTriangle,
  GitBranch,
  Key,
  XCircle,
  Clock,
  Menu,
  X
} from "lucide-react";

export default function PublicLandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [demoModalOpen, setDemoModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#FCFCFA] text-[#1F1F1F] font-sans selection:bg-[#EAF7EE] selection:text-[#2E9D50]">
      {/* 1. STICKY HEADER */}
      <header className="sticky top-0 z-50 bg-[#FCFCFA]/90 backdrop-blur-md border-b border-[#E8E8E4] transition-all">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Logo Left */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-[10px] bg-[#EAF7EE] border border-[#2E9D50]/30 flex items-center justify-center p-2 group-hover:border-[#2E9D50] transition-colors">
              <Image
                src="/logo.png"
                alt="AGENTGUARD Logo"
                width={32}
                height={32}
                className="object-contain"
              />
            </div>
            <div>
              <span className="text-[19px] font-bold text-[#1F1F1F] tracking-tight block leading-tight">
                AGENTGUARD
              </span>
              <span className="text-[10px] font-bold text-[#2E9D50] uppercase tracking-wider block">
                Runtime Control Plane
              </span>
            </div>
          </Link>

          {/* Navigation Center */}
          <nav className="hidden md:flex items-center gap-8 text-[13px] font-medium text-[#666666]">
            <a href="#platform" className="hover:text-[#1F1F1F] transition-colors">
              Platform
            </a>
            <a href="#governance" className="hover:text-[#1F1F1F] transition-colors">
              AI Governance
            </a>
            <a href="#security" className="hover:text-[#1F1F1F] transition-colors">
              Security
            </a>
            <a href="#runtime" className="hover:text-[#1F1F1F] transition-colors">
              Runtime Control
            </a>
            <a href="#organizations" className="hover:text-[#1F1F1F] transition-colors">
              Organizations
            </a>
            <a href="#pricing" className="hover:text-[#1F1F1F] transition-colors">
              Pricing
            </a>
          </nav>

          {/* Right Action CTAs */}
          <div className="hidden md:flex items-center gap-4 text-[13px]">
            <Link
              href="/login"
              className="px-4 py-2 font-bold text-[#1F1F1F] hover:text-[#2E9D50] transition-colors"
            >
              Sign In
            </Link>
            <button
              onClick={() => setDemoModalOpen(true)}
              className="px-4 py-2 bg-[#FCFCFA] hover:bg-[#F2F2EE] text-[#1F1F1F] border border-[#E8E8E4] font-bold rounded-[8px] transition-colors shadow-xs"
            >
              Request Demo
            </button>
            <Link
              href="/register"
              className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[8px] transition-colors shadow-sm"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Trigger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-[#666666] hover:text-[#1F1F1F]"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Dropdown Nav */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-[#E8E8E4] bg-[#FCFCFA] px-6 py-4 space-y-3">
            <a
              href="#platform"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-[14px] font-medium text-[#666666]"
            >
              Platform
            </a>
            <a
              href="#governance"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-[14px] font-medium text-[#666666]"
            >
              AI Governance
            </a>
            <a
              href="#security"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-[14px] font-medium text-[#666666]"
            >
              Security
            </a>
            <a
              href="#runtime"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-[14px] font-medium text-[#666666]"
            >
              Runtime Control
            </a>
            <a
              href="#organizations"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-[14px] font-medium text-[#666666]"
            >
              Organizations
            </a>
            <div className="pt-3 border-t border-[#E8E8E4] flex flex-col gap-2">
              <Link
                href="/login"
                className="w-full text-center py-2 text-[14px] font-bold text-[#1F1F1F] border border-[#E8E8E4] rounded-[8px]"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="w-full text-center py-2 text-[14px] font-bold bg-[#2E9D50] text-white rounded-[8px]"
              >
                Get Started
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* 2. HERO SECTION */}
      <section className="pt-16 pb-24 border-b border-[#E8E8E4] relative overflow-hidden">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Left Content */}
            <div className="lg:col-span-6 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-full text-[12px] font-bold text-[#237A3C]">
                <Shield className="w-3.5 h-3.5" />
                <span>Enterprise AI Governance Platform</span>
              </div>

              <h1 className="text-[42px] sm:text-[54px] font-bold text-[#1F1F1F] tracking-tight leading-[1.1]">
                Control Every AI Agent. <br />
                <span className="text-[#2E9D50]">Govern Every Decision.</span>
              </h1>

              <p className="text-[16px] sm:text-[17px] text-[#666666] leading-relaxed max-w-xl">
                AGENTGUARD gives enterprises a unified control plane for AI agent identity,
                permissions, runtime behavior, security, governance and auditability.
              </p>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 pt-2">
                <Link
                  href="/register"
                  className="px-7 py-3.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[14px] font-bold rounded-[8px] text-center transition-colors shadow-md flex items-center justify-center gap-2"
                >
                  <span>Get Started</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>

                <a
                  href="#platform"
                  className="px-7 py-3.5 bg-[#FFFFFF] hover:bg-[#F2F2EE] text-[#1F1F1F] border border-[#E8E8E4] text-[14px] font-bold rounded-[8px] text-center transition-colors shadow-xs"
                >
                  Explore Platform
                </a>
              </div>

              <div className="pt-6 border-t border-[#E8E8E4] grid grid-cols-3 gap-4 text-[12px] text-[#666666]">
                <div>
                  <span className="font-bold text-[#1F1F1F] block text-[15px]">Zero-Trust</span>
                  <span>Agent Identity System</span>
                </div>
                <div>
                  <span className="font-bold text-[#1F1F1F] block text-[15px]">Right-to-Refuse</span>
                  <span>Runtime Policy Engine</span>
                </div>
                <div>
                  <span className="font-bold text-[#1F1F1F] block text-[15px]">Black Box</span>
                  <span>Causal Audit Provenance</span>
                </div>
              </div>
            </div>

            {/* Right Visual: Control Plane Pipeline Flow */}
            <div className="lg:col-span-6">
              <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] p-6 shadow-xl space-y-6">
                <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-4">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-[#2E9D50]" />
                    <span className="text-[14px] font-bold text-[#1F1F1F]">
                      AGENTGUARD Runtime Control Pipeline
                    </span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded">
                    ACTIVE CONTROL
                  </span>
                </div>

                {/* Pipeline Flow Steps */}
                <div className="space-y-3 relative text-[12px]">
                  {/* Step 1 */}
                  <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Bot className="w-4 h-4 text-[#8064C8]" />
                      <span className="font-bold text-[#1F1F1F]">1. Autonomous AI Agent Request</span>
                    </div>
                    <span className="font-mono text-[11px] text-[#666666]">RefundAgent (AG-101)</span>
                  </div>

                  {/* Step 2 */}
                  <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Key className="w-4 h-4 text-[#2878D4]" />
                      <span className="font-bold text-[#1F1F1F]">2. Agent Passport & Capability Token</span>
                    </div>
                    <span className="px-2 py-0.5 bg-[#FCFCFA] border border-[#E8E8E4] text-[10px] font-bold text-[#2878D4] rounded">
                      PSP-VERIFIED
                    </span>
                  </div>

                  {/* Step 3 */}
                  <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Layers className="w-4 h-4 text-[#F59A23]" />
                      <span className="font-bold text-[#1F1F1F]">3. Policy Engine Evaluation</span>
                    </div>
                    <span className="text-[11px] font-mono text-[#666666]">Threshold: ₹5,000</span>
                  </div>

                  {/* Step 4 */}
                  <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Activity className="w-4 h-4 text-[#8064C8]" />
                      <span className="font-bold text-[#1F1F1F]">4. Risk Engine Scoring</span>
                    </div>
                    <span className="font-bold text-[#8064C8]">Score: 28 / 100</span>
                  </div>

                  {/* Step 5 */}
                  <div className="p-3.5 bg-[#EAF7EE]/60 border border-[#2E9D50]/40 rounded-[8px] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Shield className="w-4.5 h-4.5 text-[#237A3C]" />
                      <span className="font-bold text-[#1F1F1F]">5. Right-to-Refuse Decision</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="px-2.5 py-0.5 bg-[#EAF7EE] text-[#237A3C] text-[11px] font-bold border border-[#2E9D50]/40 rounded">
                        ALLOW
                      </span>
                      <span className="px-2 py-0.5 bg-[#FFF4D9] text-[#F59A23] text-[10px] font-bold rounded opacity-60">
                        REVIEW
                      </span>
                      <span className="px-2 py-0.5 bg-[#FDECEC] text-[#C62828] text-[10px] font-bold rounded opacity-60">
                        REFUSE
                      </span>
                    </div>
                  </div>
                </div>

                {/* Autonomy & Governance Distinction Banner */}
                <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[11px]">
                  <div className="flex items-center justify-between text-[#666666]">
                    <span>Autonomy Tiers:</span>
                    <div className="flex items-center gap-1.5 font-bold">
                      <span className="px-1.5 py-0.5 bg-white border border-[#E8E8E4] rounded">LOW</span>
                      <span className="px-1.5 py-0.5 bg-white border border-[#E8E8E4] rounded text-[#2E9D50]">MEDIUM</span>
                      <span className="px-1.5 py-0.5 bg-white border border-[#E8E8E4] rounded">HIGH</span>
                      <span className="px-1.5 py-0.5 bg-white border border-[#E8E8E4] rounded">FULL</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[#E8E8E4] flex items-center justify-between text-[#1F1F1F]">
                    <span className="font-bold text-[#237A3C]">Core Architectural Guardrail:</span>
                    <span className="font-mono text-[10px] bg-[#EAF7EE] px-2 py-0.5 rounded border border-[#2E9D50]/30 font-bold">
                      IAM Role ≠ Autonomy Level ≠ Governance Decision
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. TRUST / CONTROL SECTION & FEATURES */}
      <section id="platform" className="py-24 border-b border-[#E8E8E4] bg-[#FFFFFF]">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
          <div className="text-center max-w-3xl mx-auto space-y-4">
            <h2 className="text-[32px] sm:text-[40px] font-bold text-[#1F1F1F] tracking-tight">
              AI Agents Need an Enterprise Control Plane
            </h2>
            <p className="text-[15px] text-[#666666] leading-relaxed">
              Deploying autonomous AI agents into operational workflows without runtime governance
              creates unmanaged security, financial, and compliance risk. AGENTGUARD provides the missing control layer.
            </p>
          </div>

          {/* 8 Feature Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Card 1 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center border border-[#2E9D50]/30">
                <Bot className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">1. Agent Passport</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Verifiable digital passport issued to every AI agent defining Agent ID, Owner, Purpose, Allowed Tasks, Tools, Autonomy Tier & Risk Limits.
              </p>
            </div>

            {/* Card 2 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#F1EDFA] text-[#8064C8] flex items-center justify-center border border-[#8064C8]/30">
                <Shield className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">2. 9-Role IAM Hierarchy</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Strict organization role scoping (<span className="font-mono">USER</span> $\to$ <span className="font-mono">ADMIN</span>). <span className="font-mono text-[#8064C8] font-bold">SUPER_ADMIN</span> is platform-isolated and never exposed as an org role.
              </p>
            </div>

            {/* Card 3 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center border border-[#2E9D50]/30">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">3. Policy Engine</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Deterministic rule engine evaluating resource targets, transaction values, and data sensitivity before allowing any agent execution.
              </p>
            </div>

            {/* Card 4 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#FFF4D9] text-[#F59A23] flex items-center justify-center border border-[#F59A23]/30">
                <Activity className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">4. Risk Intelligence</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Continuous dynamic scoring (0 - 100) evaluating agent trust scores, behavioral anomalies, payload velocity, and threat indicators.
              </p>
            </div>

            {/* Card 5 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#FFF4D9] text-[#F59A23] flex items-center justify-center border border-[#F59A23]/30">
                <UserCheck className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">5. Human Approvals</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Automatically routes high-value or high-risk AI operations to designated human decision makers (<span className="font-mono">MANAGER</span> / <span className="font-mono">ADMIN</span>).
              </p>
            </div>

            {/* Card 6 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#FDECEC] text-[#C62828] flex items-center justify-center border border-[#C62828]/30">
                <Zap className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">6. Circuit Breaker</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Instantly trips and freezes an AI agent's execution capabilities upon detecting anomalous behavior, policy violations, or security threats.
              </p>
            </div>

            {/* Card 7 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#F1EDFA] text-[#8064C8] flex items-center justify-center border border-[#8064C8]/30">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">7. Decision Black Box</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Immutable record logging intent summary, policy rules evaluated, risk scores, governance outcome (<span className="font-mono">ALLOW / REVIEW / REFUSE</span>), and approvers.
              </p>
            </div>

            {/* Card 8 */}
            <div className="p-6 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[14px] space-y-3 hover:border-[#2E9D50]/50 transition-colors shadow-xs">
              <div className="w-10 h-10 rounded-[8px] bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center border border-[#2E9D50]/30">
                <GitBranch className="w-5 h-5" />
              </div>
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">8. Causal Audit Provenance</h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                Complete forensic graph tracing every downstream action back to its triggering user, AI agent model version, capability token, and policy rule.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 4. REAL-TIME CONTROL SECTION */}
      <section id="governance" className="py-24 border-b border-[#E8E8E4] bg-[#FCFCFA]">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-[30px] sm:text-[36px] font-bold text-[#1F1F1F] tracking-tight">
              See What Your AI Agents Are Doing — In Real Time
            </h2>
            <p className="text-[14px] text-[#666666]">
              Real-time monitoring telemetry, governance decision stream, and SOC security controls.
            </p>
          </div>

          {/* Real-time Dashboard Placeholder Mockup */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] p-6 shadow-lg space-y-6">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-[12px]">
              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] block">ACTIVE AGENTS</span>
                <span className="text-[20px] font-bold text-[#1F1F1F]">24</span>
                <span className="text-[10px] text-[#2E9D50] font-bold block">● Operational</span>
              </div>
              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] block">RISK EVENTS</span>
                <span className="text-[20px] font-bold text-[#1F1F1F]">3</span>
                <span className="text-[10px] text-[#F59A23] font-bold block">▲ Low Anomaly</span>
              </div>
              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] block">POLICY DECISIONS</span>
                <span className="text-[20px] font-bold text-[#1F1F1F]">1,420</span>
                <span className="text-[10px] text-[#2E9D50] font-bold block">100% Evaluated</span>
              </div>
              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] block">HUMAN APPROVALS</span>
                <span className="text-[20px] font-bold text-[#1F1F1F]">2 Pending</span>
                <span className="text-[10px] text-[#2878D4] font-bold block">Manager Review</span>
              </div>
              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] space-y-1 col-span-2 sm:col-span-1">
                <span className="text-[10px] font-bold text-[#666666] block">SECURITY EVENTS</span>
                <span className="text-[20px] font-bold text-[#1F1F1F]">0 Threats</span>
                <span className="text-[10px] text-[#2E9D50] font-bold block">Normal Status</span>
              </div>
            </div>

            {/* Mock Telemetry Feed */}
            <div className="border border-[#E8E8E4] rounded-[10px] overflow-hidden text-[12px]">
              <div className="bg-[#FCFCFA] px-4 py-3 border-b border-[#E8E8E4] font-bold text-[#1F1F1F] flex items-center justify-between">
                <span>Live Agent Governance Stream</span>
                <span className="text-[10px] font-mono text-[#666666]">WebSocket Feed: Connected</span>
              </div>
              <div className="divide-y divide-[#E8E8E4] bg-white font-mono text-[11px]">
                <div className="p-3 flex items-center justify-between">
                  <span className="text-[#666666]">12:44:02 UTC</span>
                  <span className="font-bold text-[#1F1F1F]">RefundAgent</span>
                  <span>Resource: customer_refunds</span>
                  <span className="text-[#237A3C] font-bold px-2 py-0.5 bg-[#EAF7EE] rounded">ALLOW (Score: 24)</span>
                </div>
                <div className="p-3 flex items-center justify-between">
                  <span className="text-[#666666]">12:43:55 UTC</span>
                  <span className="font-bold text-[#1F1F1F]">FraudMonitorAgent</span>
                  <span>Action: transaction_review</span>
                  <span className="text-[#F59A23] font-bold px-2 py-0.5 bg-[#FFF4D9] rounded">REVIEW (Manager Alert)</span>
                </div>
                <div className="p-3 flex items-center justify-between">
                  <span className="text-[#666666]">12:41:10 UTC</span>
                  <span className="font-bold text-[#1F1F1F]">CustomerSupportAgent</span>
                  <span>Target: account_deletion</span>
                  <span className="text-[#C62828] font-bold px-2 py-0.5 bg-[#FDECEC] rounded">REFUSE (Policy Violation)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. MULTI-TENANT ENTERPRISE SECTION */}
      <section id="organizations" className="py-24 border-b border-[#E8E8E4] bg-[#FFFFFF]">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
          <div className="text-center max-w-3xl mx-auto space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-full text-[12px] font-bold text-[#237A3C]">
              <Building2 className="w-3.5 h-3.5" />
              <span>Multi-Tenant Enterprise Architecture</span>
            </div>
            <h2 className="text-[32px] sm:text-[40px] font-bold text-[#1F1F1F] tracking-tight">
              One Control Plane. Every Organization.
            </h2>
            <p className="text-[15px] text-[#666666] leading-relaxed">
              AGENTGUARD provides strict tenant boundary isolation for multi-organization deployments. Each organization receives a dedicated workspace with zero cross-tenant data leakage.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
            {/* Left Isolation Highlights */}
            <div className="space-y-4 text-[13px]">
              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-[#2E9D50] shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-[#1F1F1F] block">Isolated Tenant Workspaces</span>
                  <span className="text-[#666666]">
                    Users, agents, policies, audit logs, and reports are strictly scoped to the active organization tenant via PostgreSQL RLS.
                  </span>
                </div>
              </div>

              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-[#2E9D50] shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-[#1F1F1F] block">Platform Super Admin Scoping</span>
                  <span className="text-[#666666]">
                    <span className="font-mono text-[#8064C8] font-bold">SUPER_ADMIN</span> is platform-level identity controlling global organization licenses. <span className="font-mono">SUPER_ADMIN</span> is NEVER listed inside an organization's IAM user list.
                  </span>
                </div>
              </div>

              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-[#2E9D50] shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-[#1F1F1F] block">License & Quota Controls</span>
                  <span className="text-[#666666]">
                    Enterprise SaaS plans (<span className="font-mono">ENTERPRISE</span>, <span className="font-mono">PROFESSIONAL</span>, <span className="font-mono">STARTER</span>) enforce hard seat quotas and agent limits per tenant.
                  </span>
                </div>
              </div>
            </div>

            {/* Right Branding Preview Card */}
            <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[16px] p-8 shadow-sm space-y-6">
              <div className="text-[12px] font-bold text-[#666666] uppercase tracking-wider">
                Organization Dual Visual Identity Example
              </div>

              {/* Branding Visual Example Header */}
              <div className="p-4 bg-white border border-[#E8E8E4] rounded-[12px] flex items-center justify-between shadow-xs">
                {/* Platform Identity */}
                <div className="flex items-center gap-2">
                  <Image src="/logo.png" alt="AGENTGUARD Logo" width={24} height={24} />
                  <span className="font-bold text-[14px] text-[#1F1F1F]">AGENTGUARD</span>
                </div>

                {/* Tenant Brand */}
                <div className="text-right">
                  <span className="font-bold text-[13px] text-[#1F1F1F] block">ACME TECHNOLOGIES</span>
                  <span className="text-[10px] font-bold text-[#2E9D50]">licensed by AGENTGUARD</span>
                </div>
              </div>

              <p className="text-[12px] text-[#666666] leading-relaxed">
                Every organization maintains its own visual identity, custom logo, and administrative control, while AGENTGUARD provides the underlying governance runtime.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. SECURITY ARCHITECTURE SECTION */}
      <section id="security" className="py-24 border-b border-[#E8E8E4] bg-[#FCFCFA]">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
          <div className="text-center max-w-3xl mx-auto space-y-4">
            <h2 className="text-[32px] sm:text-[40px] font-bold text-[#1F1F1F] tracking-tight">
              Security Is Built Into the Runtime
            </h2>
            <p className="text-[15px] text-[#666666] leading-relaxed">
              AGENTGUARD enforces zero-trust validation at every layer of execution, from HTTP request authorization down to database RLS policy enforcement.
            </p>
          </div>

          {/* Security Pipeline Flow */}
          <div className="grid grid-cols-2 md:grid-cols-9 gap-2 text-center text-[11px] font-bold">
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#2878D4] block font-mono">01</span>
              <span>Identity</span>
            </div>
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#2878D4] block font-mono">02</span>
              <span>Auth</span>
            </div>
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#2878D4] block font-mono">03</span>
              <span>Authorization</span>
            </div>
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#F59A23] block font-mono">04</span>
              <span>Policy</span>
            </div>
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#8064C8] block font-mono">05</span>
              <span>Risk</span>
            </div>
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#237A3C] block font-mono">06</span>
              <span>Decision</span>
            </div>
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#2E9D50] block font-mono">07</span>
              <span>Execution</span>
            </div>
            <div className="p-3 bg-white border border-[#E8E8E4] rounded-[8px] space-y-1">
              <span className="text-[#666666] block font-mono">08</span>
              <span>Audit</span>
            </div>
            <div className="p-3 bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-[8px] space-y-1 col-span-2 md:col-span-1">
              <span className="text-[#237A3C] block font-mono">09</span>
              <span className="text-[#237A3C]">Verified</span>
            </div>
          </div>
        </div>
      </section>

      {/* 7. ENTERPRISE REPORTING SECTION */}
      <section id="runtime" className="py-24 border-b border-[#E8E8E4] bg-[#FFFFFF]">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
          <div className="text-center max-w-3xl mx-auto space-y-4">
            <h2 className="text-[32px] sm:text-[40px] font-bold text-[#1F1F1F] tracking-tight">
              Everything Auditable. Everything Reportable.
            </h2>
            <p className="text-[15px] text-[#666666] leading-relaxed">
              Export comprehensive compliance PDF documents and openpyxl Excel workbooks generated directly from real PostgreSQL database execution records.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-[13px]">
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <FileText className="w-5 h-5 text-[#C62828]" />
              <span>PDF Reports</span>
            </div>
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <FileSpreadsheet className="w-5 h-5 text-[#2E9D50]" />
              <span>Excel Reports</span>
            </div>
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <FileText className="w-5 h-5 text-[#2878D4]" />
              <span>CSV Datasets</span>
            </div>
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <Shield className="w-5 h-5 text-[#8064C8]" />
              <span>Audit Reports</span>
            </div>
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <Lock className="w-5 h-5 text-[#F59A23]" />
              <span>Security Reports</span>
            </div>
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <Activity className="w-5 h-5 text-[#8064C8]" />
              <span>Risk Reports</span>
            </div>
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <Bot className="w-5 h-5 text-[#2E9D50]" />
              <span>Agent Reports</span>
            </div>
            <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] flex items-center gap-3 font-bold text-[#1F1F1F]">
              <Layers className="w-5 h-5 text-[#2878D4]" />
              <span>Governance Reports</span>
            </div>
          </div>

          <div className="text-center pt-4">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-[#1F1F1F] hover:bg-[#333333] text-white text-[14px] font-bold rounded-[8px] transition-colors"
            >
              <span>See the Platform</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* 8. FINAL CTA SECTION */}
      <section id="pricing" className="py-24 bg-[#FCFCFA] border-b border-[#E8E8E4]">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-8">
          <h2 className="text-[36px] sm:text-[46px] font-bold text-[#1F1F1F] tracking-tight">
            Build AI Systems You Can Trust.
          </h2>
          <p className="text-[16px] text-[#666666] leading-relaxed max-w-2xl mx-auto">
            AGENTGUARD gives organizations the infrastructure to deploy autonomous AI without losing control, visibility or accountability.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
            <Link
              href="/register"
              className="w-full sm:w-auto px-8 py-4 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[15px] font-bold rounded-[8px] transition-colors shadow-md flex items-center justify-center gap-2"
            >
              <span>Get Started</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <button
              onClick={() => setDemoModalOpen(true)}
              className="w-full sm:w-auto px-8 py-4 bg-[#FFFFFF] hover:bg-[#F2F2EE] text-[#1F1F1F] border border-[#E8E8E4] text-[15px] font-bold rounded-[8px] transition-colors shadow-xs"
            >
              Request Demo
            </button>
          </div>
        </div>
      </section>

      {/* 9. FOOTER */}
      <footer className="bg-[#FFFFFF] py-16 border-t border-[#E8E8E4] text-[13px] text-[#666666]">
        <div className="max-w-[1300px] mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-8">
            {/* Col 1 Brand */}
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-center gap-2">
                <Image src="/logo.png" alt="AGENTGUARD Logo" width={28} height={28} />
                <span className="font-bold text-[18px] text-[#1F1F1F]">AGENTGUARD</span>
              </div>
              <p className="text-[12px] text-[#666666] leading-relaxed max-w-sm">
                AI Agent Governance & Runtime Control Plane for Autonomous AI Employees.
              </p>
            </div>

            {/* Col 2 Nav */}
            <div className="space-y-2">
              <span className="font-bold text-[#1F1F1F] block mb-2">Platform</span>
              <a href="#platform" className="block hover:text-[#1F1F1F]">Security Controls</a>
              <a href="#governance" className="block hover:text-[#1F1F1F]">Policy Engine</a>
              <a href="#runtime" className="block hover:text-[#1F1F1F]">Runtime Black Box</a>
            </div>

            {/* Col 3 Org */}
            <div className="space-y-2">
              <span className="font-bold text-[#1F1F1F] block mb-2">Enterprise</span>
              <a href="#organizations" className="block hover:text-[#1F1F1F]">Multi-Tenant Workspaces</a>
              <a href="#pricing" className="block hover:text-[#1F1F1F]">License Quotas</a>
              <Link href="/login" className="block hover:text-[#1F1F1F]">Control Plane Sign In</Link>
            </div>

            {/* Col 4 Legal */}
            <div className="space-y-2">
              <span className="font-bold text-[#1F1F1F] block mb-2">Legal & Security</span>
              <span className="block text-[#666666]">Privacy Policy</span>
              <span className="block text-[#666666]">Terms of Service</span>
              <span className="block text-[#666666]">Zero-Trust Security</span>
            </div>
          </div>

          <div className="pt-8 border-t border-[#E8E8E4] flex flex-col sm:flex-row items-center justify-between text-[12px] text-[#666666] gap-4">
            <span>© {new Date().getFullYear()} AGENTGUARD. All rights reserved.</span>
            <div className="flex items-center gap-6">
              <span>Privacy</span>
              <span>Terms</span>
              <span>Security</span>
            </div>
          </div>
        </div>
      </footer>

      {/* REQUEST DEMO MODAL */}
      {demoModalOpen && (
        <div className="fixed inset-0 z-50 bg-[#1F1F1F]/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] max-w-md w-full p-6 shadow-2xl space-y-4 relative">
            <button
              onClick={() => setDemoModalOpen(false)}
              className="absolute top-4 right-4 text-[#666666] hover:text-[#1F1F1F]"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="space-y-1">
              <h3 className="text-[20px] font-bold text-[#1F1F1F]">Request Enterprise Demo</h3>
              <p className="text-[12px] text-[#666666]">
                Schedule a 1-on-1 walkthrough of the AGENTGUARD Runtime Control Plane with our AI Security engineering team.
              </p>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                alert("Thank you! Your enterprise demo request has been received. Our team will contact you shortly.");
                setDemoModalOpen(false);
              }}
              className="space-y-3 text-[13px]"
            >
              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Work Email</label>
                <input
                  type="email"
                  required
                  placeholder="name@company.com"
                  className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Organization Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Corporation"
                  className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                />
              </div>

              <button
                type="submit"
                className="w-full py-3 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[8px] transition-colors mt-2"
              >
                Submit Demo Request
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
