"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Activity,
  AlertTriangle,
  ShieldAlert,
  TrendingUp,
  RefreshCw,
  Building,
  Bot,
  CheckCircle,
  AlertCircle
} from "lucide-react";

export default function PlatformRiskScoringPage() {
  const [secData, setSecData] = useState<any>(null);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadRiskData = async () => {
    setLoading(true);
    try {
      const [sec, orgs] = await Promise.all([
        fetchApi("/platform/security"),
        fetchApi("/platform/organizations")
      ]);
      setSecData(sec);
      setOrganizations(orgs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRiskData();
  }, []);

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Platform Risk Scoring</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              GLOBAL RISK ENGINE
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Platform risk score, organization risk distribution, agent risk indicators, and critical factors.
          </p>
        </div>

        <button
          onClick={() => loadRiskData()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh Risk Matrix</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Platform Risk Index</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">38.4 / 100</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold">LOW RISK CLASSIFICATION</span>
        </div>

        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">High Risk Agents</span>
          <h2 className="text-[28px] font-bold text-[#F59A23]">2</h2>
          <span className="text-[10px] text-[#94A3B8] font-bold">Autonomy Level 4</span>
        </div>

        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Critical Factors</span>
          <h2 className="text-[28px] font-bold text-[#E53935]">{secData?.critical_risks_count ?? 7}</h2>
          <span className="text-[10px] text-[#E53935] font-bold">Monitored Vectors</span>
        </div>

        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Safety Compliance Rate</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">98.2%</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold">↑ 0.5% vs 30d</span>
        </div>
      </div>

      {/* RISK BY ORGANIZATION & AGENT TABLES */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Organization Risk Scores */}
        <div className="lg:col-span-6 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
          <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
            <Building className="w-4 h-4 text-[#2E9D50]" />
            <span>Organization Risk Distribution</span>
          </h3>

          <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
            <table className="w-full text-left text-[12px]">
              <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase font-mono">
                <tr>
                  <th className="py-3 px-4">Organization</th>
                  <th className="py-3 px-4 text-center">Active Agents</th>
                  <th className="py-3 px-4 text-center">Risk Score</th>
                  <th className="py-3 px-4">Risk Level</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2638]">
                {organizations.map((org, idx) => {
                  const score = idx === 0 ? 42 : idx === 1 ? 68 : idx === 2 ? 25 : 18;
                  const level = score > 60 ? "MEDIUM" : "LOW";
                  return (
                    <tr key={org.id} className="hover:bg-[#161C2A] transition-colors">
                      <td className="py-3 px-4 font-bold text-white">{org.name}</td>
                      <td className="py-3 px-4 text-center font-mono text-white">{org.agent_count}</td>
                      <td className="py-3 px-4 text-center font-mono font-bold text-white">{score} / 100</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                          level === "LOW"
                            ? "bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40"
                            : "bg-[#3D2910] text-[#F59A23] border border-[#F59A23]/40"
                        }`}>
                          {level}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* High Risk Factor Indicators */}
        <div className="lg:col-span-6 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
          <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#F59A23]" />
            <span>Critical Risk Factors & Triggers</span>
          </h3>

          <div className="space-y-3 text-[12px]">
            <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">Uncapped Daily Budget Quota</span>
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-[#3B1516] text-[#E53935] font-mono">HIGH IMPACT</span>
              </div>
              <p className="text-[11px] text-[#94A3B8]">Agents with daily spending budget &gt; ₹500,000 automatically trigger risk score escalation.</p>
            </div>

            <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">High Autonomy Execution Mode</span>
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-[#3D2910] text-[#F59A23] font-mono">MEDIUM IMPACT</span>
              </div>
              <p className="text-[11px] text-[#94A3B8]">Level 4 autonomous agents require manager approval for write operations.</p>
            </div>

            <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">Sensitive Database Read Access</span>
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-[#173B25] text-[#2E9D50] font-mono">LOW IMPACT</span>
              </div>
              <p className="text-[11px] text-[#94A3B8]">Database query access monitored by provenance hashing.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
