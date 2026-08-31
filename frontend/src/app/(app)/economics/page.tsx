"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { DollarSign } from "lucide-react";

export default function EconomicsPage() {
  const [budgets, setBudgets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadBudgets() {
      try {
        const data = await fetchApi("/economics/budgets").catch(() => []);
        setBudgets(data || []);
      } catch (err) {
        console.error("Budgets fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadBudgets();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Agent Economics & Financial Budgets</h1>
        <p className="text-[13px] text-[#666666]">
          Daily Financial Caps & Transaction Limits
        </p>
      </div>

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
