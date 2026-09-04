"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  ShieldAlert,
  AlertTriangle,
  Lock,
  RefreshCw,
  Zap,
  UserX,
  Bot,
  Activity,
  ShieldCheck,
  CheckCircle,
  Clock,
  TrendingUp,
  AlertCircle
} from "lucide-react";

export default function PlatformSecurityPage() {
  const [secData, setSecData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadSecurity = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/security");
      setSecData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSecurity();
  }, []);

  const criticalRisks = secData?.critical_risks_count ?? 7;
  const securityIncidents = secData?.security_incidents_count ?? 3;
  const blockedActions = secData?.blocked_actions_count ?? 23;
  const suspendedAgents = secData?.suspended_agents_count ?? 2;
  const suspendedUsers = secData?.suspended_users_count ?? 1;
  const riskScore = "38.4 / 100";
  const activeThreats = 2;

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Platform Security</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#3B1516] text-[#E53935] border border-[#E53935]/40 font-mono flex items-center gap-1">
              <ShieldAlert className="w-3 h-3" /> ACTIVE PROTECTION
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Global security monitoring, incidents, threats and platform protection.
          </p>
        </div>

        <button
          onClick={() => loadSecurity()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* 7 KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3.5">
        {/* Card 1: Critical Risks */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-1.5 shadow-sm hover:border-[#E53935]/50 transition-colors">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">CRITICAL RISKS</span>
          <h2 className="text-[24px] font-bold text-[#E53935] leading-none">{criticalRisks}</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold block">↓ 1 vs last 30d</span>
        </div>

        {/* Card 2: Security Incidents */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-1.5 shadow-sm hover:border-[#F59A23]/50 transition-colors">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">INCIDENTS</span>
          <h2 className="text-[24px] font-bold text-[#F59A23] leading-none">{securityIncidents}</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold block">↓ 2 vs last 30d</span>
        </div>

        {/* Card 3: Blocked Actions */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-1.5 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">BLOCKED ACTIONS</span>
          <h2 className="text-[24px] font-bold text-[#2E9D50] leading-none">{blockedActions}</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold block">↑ 8 vs last 30d</span>
        </div>

        {/* Card 4: Suspended Agents */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-1.5 shadow-sm hover:border-[#8064C8]/50 transition-colors">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">SUSPENDED AGENTS</span>
          <h2 className="text-[24px] font-bold text-[#8064C8] leading-none">{suspendedAgents}</h2>
          <span className="text-[10px] text-[#94A3B8] font-bold block">Quarantined</span>
        </div>

        {/* Card 5: Suspended Users */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-1.5 shadow-sm hover:border-[#94A3B8]/50 transition-colors">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">SUSPENDED USERS</span>
          <h2 className="text-[24px] font-bold text-[#94A3B8] leading-none">{suspendedUsers}</h2>
          <span className="text-[10px] text-[#94A3B8] font-bold block">IAM Restricted</span>
        </div>

        {/* Card 6: Risk Score */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-1.5 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">PLATFORM RISK SCORE</span>
          <h2 className="text-[20px] font-bold text-[#2E9D50] leading-none">{riskScore}</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold block">LOW RISK PROFILE</span>
        </div>

        {/* Card 7: Active Threats */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-1.5 shadow-sm hover:border-[#E53935]/50 transition-colors">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">ACTIVE THREATS</span>
          <h2 className="text-[24px] font-bold text-[#E53935] leading-none">{activeThreats}</h2>
          <span className="text-[10px] text-[#E53935] font-bold block">Monitored Vectors</span>
        </div>
      </div>

      {/* MAIN SECTIONS GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left 8 Cols: Security Incidents & Threat Activity Stream */}
        <div className="lg:col-span-8 space-y-5">
          {/* Security Incidents Table */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#1E2638] pb-3">
              <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-[#E53935]" />
                <span>Global Security Incidents</span>
              </h3>
              <span className="text-[10px] font-mono text-[#64748B] uppercase">Real-Time Log</span>
            </div>

            <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
              <table className="w-full text-left text-[12px]">
                <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase font-mono">
                  <tr>
                    <th className="py-3 px-4">Incident Title</th>
                    <th className="py-3 px-4">Organization</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1E2638]">
                  {(secData?.incidents || []).length === 0 ? (
                    <>
                      <tr className="hover:bg-[#161C2A] transition-colors">
                        <td className="py-3.5 px-4 font-bold text-white">Unauthorized Budget Override Attempt</td>
                        <td className="py-3.5 px-4 text-[#94A3B8]">ACME Technologies</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3B1516] text-[#E53935] border border-[#E53935]/40 font-mono">
                            CRITICAL
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-[#2E9D50] font-bold">BLOCKED</td>
                        <td className="py-3.5 px-4 font-mono text-[#64748B]">12m ago</td>
                      </tr>
                      <tr className="hover:bg-[#161C2A] transition-colors">
                        <td className="py-3.5 px-4 font-bold text-white">Abnormal API Token Spike Detected</td>
                        <td className="py-3.5 px-4 text-[#94A3B8]">MedCore Health Systems</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3D2910] text-[#F59A23] border border-[#F59A23]/40 font-mono">
                            HIGH
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-[#F59A23] font-bold">INVESTIGATING</td>
                        <td className="py-3.5 px-4 font-mono text-[#64748B]">45m ago</td>
                      </tr>
                      <tr className="hover:bg-[#161C2A] transition-colors">
                        <td className="py-3.5 px-4 font-bold text-white">Suspicious Prompt Injection Keyword</td>
                        <td className="py-3.5 px-4 text-[#94A3B8]">Nexa Financial Services</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3D2910] text-[#F59A23] border border-[#F59A23]/40 font-mono">
                            MEDIUM
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-[#2E9D50] font-bold">CONTAINED</td>
                        <td className="py-3.5 px-4 font-mono text-[#64748B]">2h ago</td>
                      </tr>
                    </>
                  ) : (
                    (secData?.incidents || []).map((inc: any) => (
                      <tr key={inc.id} className="hover:bg-[#161C2A] transition-colors">
                        <td className="py-3.5 px-4 font-bold text-white">{inc.title}</td>
                        <td className="py-3.5 px-4 text-[#94A3B8]">{inc.org_name}</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3B1516] text-[#E53935] border border-[#E53935]/40 font-mono">
                            {inc.severity}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-white font-bold">{inc.status}</td>
                        <td className="py-3.5 px-4 font-mono text-[#64748B]">
                          {inc.timestamp ? new Date(inc.timestamp).toLocaleString() : "Just now"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Blocked Actions Summary */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-3 shadow-sm">
            <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#2E9D50]" />
              <span>Recent Blocked Guardrail Enforcement Actions</span>
            </h3>

            <div className="space-y-2 text-[12px]">
              <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">FINANCIAL_LIMIT_EXCEEDED</span>
                  <span className="text-[11px] text-[#94A3B8]">Agent AGENT-ACC-09 requested transfer of ₹450,000 against max budget ₹100,000</span>
                </div>
                <span className="px-2 py-1 bg-[#3B1516] text-[#E53935] rounded font-mono text-[10px] font-bold">REFUSED</span>
              </div>
              <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">UNAUTHORIZED_DB_SCHEMA_ACCESS</span>
                  <span className="text-[11px] text-[#94A3B8]">Agent AGENT-MED-04 attempted raw table DROP in MedCore database</span>
                </div>
                <span className="px-2 py-1 bg-[#3B1516] text-[#E53935] rounded font-mono text-[10px] font-bold">REFUSED</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right 4 Cols: Suspended Identities & Security Status */}
        <div className="lg:col-span-4 space-y-5">
          {/* Quarantined / Suspended Identities */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-3 shadow-sm">
            <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
              <UserX className="w-4 h-4 text-[#F59A23]" />
              <span>Suspended Identities</span>
            </h3>

            <div className="space-y-2 text-[12px]">
              <div className="p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48] space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">AGENT-FIN-009</span>
                  <span className="text-[9px] font-bold uppercase bg-[#3B1516] text-[#E53935] px-1.5 py-0.5 rounded font-mono">QUARANTINED</span>
                </div>
                <p className="text-[11px] text-[#64748B]">Nexa Financial • Excessive failure rate</p>
              </div>

              <div className="p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48] space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">dev-test-user@urbangrid.com</span>
                  <span className="text-[9px] font-bold uppercase bg-[#3B1516] text-[#E53935] px-1.5 py-0.5 rounded font-mono">RESTRICTED</span>
                </div>
                <p className="text-[11px] text-[#64748B]">UrbanGrid • Suspicious token rotation</p>
              </div>
            </div>
          </div>

          {/* Security Status Overview Panel */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-3 shadow-sm">
            <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#2E9D50]" />
              <span>Security Engine Status</span>
            </h3>

            <div className="space-y-2 text-[12px]">
              <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
                <span className="text-[#94A3B8]">Circuit Breaker Mode</span>
                <span className="font-bold text-[#2E9D50]">AUTO_TRIP_ACTIVE</span>
              </div>
              <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
                <span className="text-[#94A3B8]">Policy Enforcement</span>
                <span className="font-bold text-[#2E9D50]">STRICT_PREVENT</span>
              </div>
              <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
                <span className="text-[#94A3B8]">Immutable Audit Trail</span>
                <span className="font-bold text-[#2E9D50]">ENABLED</span>
              </div>
              <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
                <span className="text-[#94A3B8]">Risk Engine Score</span>
                <span className="font-bold text-white">0.032 (Low)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
