"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Scale, ShieldCheck } from "lucide-react";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPolicies() {
      try {
        const data = await fetchApi("/policies").catch(() => []);
        setPolicies(data || []);
      } catch (err) {
        console.error("Policies fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadPolicies();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Governance Policy Center</h1>
        <p className="text-[13px] text-[#666666]">
          Active Enterprise Governance Rules & Right-to-Refuse Policy Limits
        </p>
      </div>

      {policies.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Scale className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Custom Policies Configured</h3>
          <p className="text-[12px] text-[#666666]">
            The platform is running default core runtime governance rules (₹5,000 automatic limit, ₹50,000 hard ceiling, zero production data drop).
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {policies.map((policy) => (
            <div key={policy.id} className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-[16px] font-bold text-[#1F1F1F]">{policy.name}</h3>
                <StatusBadge status={policy.status} />
              </div>
              <p className="text-[12px] text-[#666666]">Category: {policy.category} • Priority: {policy.priority}</p>
              <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[12px] font-mono">
                Version: {policy.version}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
