"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Activity } from "lucide-react";

export default function RiskPage() {
  const [agentsRisk, setAgentsRisk] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRisk() {
      try {
        const data = await fetchApi("/risk/agents").catch(() => []);
        setAgentsRisk(data || []);
      } catch (err) {
        console.error("Risk fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadRisk();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Risk Intelligence Matrix</h1>
        <p className="text-[13px] text-[#666666]">
          Real-Time Agent Risk Scoring (0 - 100 Index)
        </p>
      </div>

      {agentsRisk.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Activity className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Risk Scores Recorded</h3>
          <p className="text-[12px] text-[#666666]">
            No risk score data exists in the database. Register an agent in the directory to begin risk tracking.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-x-auto shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">AI AGENT</th>
                <th className="p-4">DEPARTMENT</th>
                <th className="p-4">AUTONOMY LEVEL</th>
                <th className="p-4">RISK SCORE (0 - 100)</th>
                <th className="p-4">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {agentsRisk.map((ag) => (
                <tr key={ag.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-bold text-[#1F1F1F]">
                    {ag.name} <span className="text-[11px] font-normal text-[#8064C8]">({ag.agent_code})</span>
                  </td>
                  <td className="p-4 text-[#666666]">{ag.department}</td>
                  <td className="p-4 text-[#1F1F1F] font-bold">{ag.autonomy}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-[#E8E8E4] rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full ${ag.risk_score > 60 ? "bg-[#E53935]" : ag.risk_score > 30 ? "bg-[#F59A23]" : "bg-[#2E9D50]"}`}
                          style={{ width: `${Math.min(ag.risk_score, 100)}%` }}
                        />
                      </div>
                      <span className="font-bold text-[12px]">{ag.risk_score}</span>
                    </div>
                  </td>
                  <td className="p-4"><StatusBadge status={ag.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
