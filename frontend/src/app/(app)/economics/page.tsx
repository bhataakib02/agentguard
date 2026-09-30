"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { DollarSign, TrendingUp, AlertCircle, CheckCircle, Info, Zap } from "lucide-react";

export default function EconomicsPage() {
  const [budgets, setBudgets] = useState<any[]>([]);
  const [optimData, setOptimData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [bData, oData] = await Promise.all([
          fetchApi("/economics/budgets").catch(() => []),
          fetchApi("/optimization/recommendations").catch(() => null)
        ]);
        setBudgets(bData || []);
        setOptimData(oData);
      } catch (err) {
        console.error("Economics fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Agent Economics & Cost Governance</h1>
        <p className="text-[13px] text-[#666666]">
          Daily Financial Caps, Transaction Limits & Real Telemetry Cost Optimization
        </p>
      </div>

      {/* COST OPTIMIZATION RECOMMENDATIONS SECTION */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-[#8064C8]" />
            <h2 className="text-[16px] font-bold text-[#1F1F1F]">Cost Optimization Recommendations</h2>
          </div>
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase font-mono ${
            optimData?.status === "SUFFICIENT DATA"
              ? "bg-[#EAF7EE] text-[#2E9D50] border border-[#2E9D50]/30"
              : "bg-[#FFFDF5] text-[#F59A23] border border-[#F59A23]/30"
          }`}>
            {optimData?.data_sufficiency === "SUFFICIENT" ? "DERIVED FROM REAL TELEMETRY" : "INSUFFICIENT DATA"}
          </span>
        </div>

        {optimData?.status === "INSUFFICIENT DATA" ? (
          <div className="p-4 bg-[#FFFDF5] border border-[#F59A23]/30 rounded-[8px] flex items-start gap-3 text-[12px] text-[#666666]">
            <Info className="w-4 h-4 text-[#F59A23] shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-[#1F1F1F] block">Zero Fabricated Recommendations</span>
              {optimData?.message || "Insufficient execution telemetry observed to derive statistically valid optimization recommendations."}
            </div>
          </div>
        ) : optimData?.recommendations && optimData.recommendations.length > 0 ? (
          <div className="space-y-3">
            {optimData.recommendations.map((rec: any, idx: number) => (
              <div key={idx} className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-[14px] text-[#1F1F1F]">{rec.title}</h3>
                  <span className="text-[10px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50] px-2 py-0.5 rounded font-mono">
                    CONFIDENCE: {rec.confidence}
                  </span>
                </div>
                <p className="text-[12px] text-[#666666]">
                  <strong>Supporting Metric:</strong> {rec.supporting_metric}
                </p>
                <div className="flex items-center justify-between text-[11px] font-mono text-[#8064C8] pt-1">
                  <span>Impact: {rec.estimated_impact}</span>
                  <span>Model: {rec.affected_model}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[12px] text-[#666666] p-4 bg-[#FCFCFA] rounded-[8px]">
            No cost anomalies or optimization actions detected across active telemetry.
          </div>
        )}
      </div>

      {/* FINANCIAL BUDGETS TABLE */}
      {budgets.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <DollarSign className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Budgets Configured</h3>
          <p className="text-[12px] text-[#666666]">
            No agent budget records exist in the database.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">AGENT ID</th>
                <th className="p-4">DAILY LIMIT</th>
                <th className="p-4">MONTHLY LIMIT</th>
                <th className="p-4">CURRENT DAILY SPEND</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {budgets.map((b) => (
                <tr key={b.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-mono font-bold text-[#8064C8]">{b.agent_id}</td>
                  <td className="p-4 font-bold text-[#2E9D50]">₹{b.daily_limit ? b.daily_limit.toLocaleString() : "0"}</td>
                  <td className="p-4 text-[#1F1F1F]">₹{b.monthly_limit ? b.monthly_limit.toLocaleString() : "0"}</td>
                  <td className="p-4 text-[#666666]">₹{b.current_daily_spend ? b.current_daily_spend.toLocaleString() : "0"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
