"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import KpiCard from "@/components/ui/KpiCard";
import StatusBadge from "@/components/ui/StatusBadge";
import {
  Bot,
  Shield,
  Activity,
  UserCheck,
  Zap,
  ArrowRight,
  Plus,
} from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  const userRole = user?.role || "USER";

  const [overview, setOverview] = useState<any>(null);
  const [agents, setAgents] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Evaluation Form State
  const [prompt, setPrompt] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<any>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [ovData, agData, decData] = await Promise.all([
        fetchApi("/analytics/overview").catch(() => null),
        fetchApi("/agents").catch(() => []),
        fetchApi("/decisions").catch(() => []),
      ]);

      setOverview(ovData || {});
      setAgents(agData || []);
      setDecisions(decData || []);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTestEvaluation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setEvaluating(true);
    setEvalResult(null);

    try {
      const res = await fetchApi("/decisions/evaluate", {
        method: "POST",
        body: JSON.stringify({ prompt }),
      });
      setEvalResult(res);
      setPrompt("");
      await loadData();
    } catch (err: any) {
      alert(`Evaluation Error: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  const getRoleHeader = () => {
    switch (userRole) {
      case "SUPER_ADMIN":
        return { title: "Platform Administration Dashboard", desc: "Global Multi-Tenant Control Plane, System Health & Platform Governance" };
      case "ADMIN":
        return { title: "Organization Admin Control Plane", desc: "Enterprise Identity, User Scoping, Security Policies & Workspace Governance" };
      case "SECURITY_ANALYST":
        return { title: "Security Operations (SOC) Center", desc: "Real-time Threat Monitoring, Anomaly Response & Circuit Breaker Control" };
      case "OPERATOR":
        return { title: "AI Operational Command Center", desc: "Agent Autonomy Controls, Capability Token Execution & Runtime Monitoring" };
      case "ANALYST":
        return { title: "AI Intelligence & Risk Analysis", desc: "Decision Black Box Audit, Causal Provenance Trees & Behavioral Scoring" };
      case "MANAGER":
        return { title: "Departmental Governance & Approvals", desc: "Human Request Approvals, Governance Policy Rules & Operational Budgets" };
      case "DEVELOPER":
        return { title: "Developer Platform & API Portal", desc: "REST API Configuration, Integration Webhooks & Execution Explorer" };
      case "VIEWER":
        return { title: "Read-Only Platform Intelligence", desc: "High-level Directory Overview, Trust Scores & Platform Governance Audit" };
      default:
        return { title: "Control Plane Dashboard", desc: "Real-time Database-Driven Autonomous AI Employee Governance & Security Platform" };
    }
  };

  const headerInfo = getRoleHeader();

  return (
    <div className="space-y-8">
      {/* Dynamic Role-Based Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[#E8E8E4] pb-5 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">{headerInfo.title}</h1>
            <span className="text-[10px] font-bold px-2.5 py-0.5 bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/30 rounded-full uppercase">
              {userRole}
            </span>
          </div>
          <p className="text-[13px] text-[#666666] mt-1">{headerInfo.desc}</p>
        </div>

        {["ADMIN", "SUPER_ADMIN", "OPERATOR"].includes(userRole) && (
          <Link
            href="/agents/create"
            className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[13px] font-bold rounded-[8px] flex items-center gap-2 transition-colors shrink-0 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Register AI Agent</span>
          </Link>
        )}
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="TOTAL AI AGENTS"
          value={overview?.total_agents || agents.length || 0}
          subtext={`${agents.filter((a) => a.status === "ACTIVE").length} Active Operational`}
          icon={Bot}
          iconBgColor="#EAF7EE"
          iconColor="#2E9D50"
        />

        <KpiCard
          label="DECISIONS EVALUATED"
          value={overview?.total_decisions || decisions.length || 0}
          subtext={`${decisions.filter((d) => d.decision === "ALLOW").length} Approved / ${
            decisions.filter((d) => d.decision === "REFUSE").length
          } Refused`}
          icon={Shield}
          iconBgColor="#EAF7EE"
          iconColor="#2E9D50"
        />

        <KpiCard
          label="PENDING APPROVALS"
          value={overview?.pending_approvals || 0}
          subtext="Requires Managerial Action"
          icon={UserCheck}
          iconBgColor="#FFF4D9"
          iconColor="#F59A23"
        />

        <KpiCard
          label="AVG PLATFORM RISK"
          value={`${overview?.avg_risk_score || 0} / 100`}
          subtext="Live Database Risk Index"
          icon={Activity}
          iconBgColor="#F1EDFA"
          iconColor="#8064C8"
        />
      </div>

      {/* Interactive Action Evaluator Widget */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-[#2E9D50]" />
            <h3 className="text-[16px] font-bold text-[#1F1F1F]">Interactive Action Evaluator</h3>
          </div>
          <span className="text-[11px] font-bold text-[#666666]">Zero-Trust Policy Engine</span>
        </div>

        <form onSubmit={handleTestEvaluation} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Issue a refund of ₹3,500 for customer 9281 or Transfer ₹75,000"
              className="flex-1 p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
            />
            <button
              type="submit"
              disabled={evaluating || !prompt.trim()}
              className="px-6 py-3 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[13px] font-bold rounded-[8px] transition-colors disabled:opacity-50 shrink-0"
            >
              {evaluating ? "Evaluating..." : "Evaluate Action"}
            </button>
          </div>
        </form>

        {evalResult && (
          <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[12px]">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#1F1F1F]">Evaluation Result:</span>
              <span className={`px-2.5 py-0.5 font-bold rounded ${
                evalResult.decision === "ALLOW"
                  ? "bg-[#EAF7EE] text-[#237A3C]"
                  : evalResult.decision === "REVIEW"
                  ? "bg-[#FFF4D9] text-[#F59A23]"
                  : "bg-[#FDECEC] text-[#C62828]"
              }`}>
                {evalResult.decision}
              </span>
            </div>
            <p className="text-[#666666]">{evalResult.reason}</p>
          </div>
        )}
      </div>

      {/* Agents & Decisions Overview Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Registered Agents */}
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
            <h3 className="text-[15px] font-bold text-[#1F1F1F]">Registered AI Employees</h3>
            <Link href="/agents" className="text-[12px] font-bold text-[#2E9D50] hover:underline flex items-center gap-1">
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {agents.length === 0 ? (
            <div className="p-8 text-center space-y-2 text-[#666666]">
              <Bot className="w-8 h-8 mx-auto opacity-30" />
              <p className="text-[12px]">Zero Agents Registered in Database.</p>
            </div>
          ) : (
            <div className="divide-y divide-[#E8E8E4]">
              {agents.slice(0, 5).map((ag) => (
                <div key={ag.id} className="py-3 flex items-center justify-between text-[13px]">
                  <div>
                    <span className="font-bold text-[#1F1F1F] block">{ag.name}</span>
                    <span className="text-[11px] text-[#666666] font-mono">{ag.agent_code}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] font-bold px-2 py-0.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded text-[#666666]">
                      Autonomy: {ag.autonomy_level}
                    </span>
                    <StatusBadge status={ag.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Decision Stream */}
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
            <h3 className="text-[15px] font-bold text-[#1F1F1F]">Decision Black Box Stream</h3>
            <Link href="/decisions" className="text-[12px] font-bold text-[#2E9D50] hover:underline flex items-center gap-1">
              <span>Audit Stream</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {decisions.length === 0 ? (
            <div className="p-8 text-center space-y-2 text-[#666666]">
              <Shield className="w-8 h-8 mx-auto opacity-30" />
              <p className="text-[12px]">No governance decision records exist in database.</p>
            </div>
          ) : (
            <div className="divide-y divide-[#E8E8E4]">
              {decisions.slice(0, 5).map((d) => (
                <div key={d.id} className="py-3 flex items-center justify-between text-[12px]">
                  <div className="space-y-0.5">
                    <span className="font-bold text-[#1F1F1F] block">{d.action_type || "Runtime Evaluation"}</span>
                    <span className="text-[#666666] text-[11px] line-clamp-1">{d.reason}</span>
                  </div>
                  <span className={`px-2 py-0.5 text-[11px] font-bold rounded ${
                    d.decision === "ALLOW"
                      ? "bg-[#EAF7EE] text-[#237A3C]"
                      : d.decision === "REVIEW"
                      ? "bg-[#FFF4D9] text-[#F59A23]"
                      : "bg-[#FDECEC] text-[#C62828]"
                  }`}>
                    {d.decision}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
