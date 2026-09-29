"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Scale, Power } from "lucide-react";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState<string | null>(null);

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

  useEffect(() => {
    loadPolicies();
  }, []);

  const handleToggle = async (policyId: string) => {
    setTogglingId(policyId);
    try {
      await fetchApi(`/policies/${policyId}/toggle`, { method: "POST" });
      await loadPolicies();
    } catch (err) {
      console.error("Failed to toggle policy status:", err);
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Governance Policy Center</h1>
        <p className="text-[13px] text-[#666666]">
          Active Enterprise Governance Rules & Right-to-Refuse Policy Limits
        </p>
      </div>

      {loading ? (
        <div className="p-8 text-center text-[#666666] text-sm">Loading governance policies...</div>
      ) : policies.length === 0 ? (
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
            <div key={policy.id} className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-[16px] font-bold text-[#1F1F1F]">{policy.name}</h3>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={policy.status} />
                    <button
                      onClick={() => handleToggle(policy.id)}
                      disabled={togglingId === policy.id}
                      title={policy.status === "ACTIVE" ? "Deactivate policy" : "Activate policy"}
                      className={`p-1 rounded text-xs border transition-colors ${
                        policy.status === "ACTIVE"
                          ? "border-[#E8E8E4] text-[#666666] hover:bg-[#FEE2E2] hover:text-[#DC2626]"
                          : "border-[#E8E8E4] text-[#666666] hover:bg-[#DCFCE7] hover:text-[#16A34A]"
                      }`}
                    >
                      <Power className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                <p className="text-[12px] text-[#666666]">
                  Category: <span className="font-semibold text-[#1F1F1F]">{policy.category}</span> • Priority: <span className="font-semibold text-[#1F1F1F]">{policy.priority}</span>
                </p>

                {/* Rules Section */}
                <div className="space-y-2 pt-2 border-t border-[#F0F0EE]">
                  <div className="text-[11px] font-semibold text-[#888888] uppercase tracking-wider">
                    Enforcement Rules ({policy.rules?.length || policy.rules_count || 0})
                  </div>
                  {policy.rules && policy.rules.length > 0 ? (
                    <div className="space-y-1.5">
                      {policy.rules.map((rule: any) => (
                        <div key={rule.id} className="flex items-center justify-between bg-[#F8F9FA] px-2.5 py-1.5 rounded-[6px] text-[11px]">
                          <span className="font-mono text-[#1F1F1F]">{rule.condition_expression}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            rule.decision_output === "REFUSE" ? "bg-[#FEE2E2] text-[#DC2626]" :
                            rule.decision_output === "REVIEW" ? "bg-[#FEF3C7] text-[#D97706]" :
                            "bg-[#DCFCE7] text-[#16A34A]"
                          }`}>
                            {rule.decision_output}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-[#999999] italic">No custom rules specified</p>
                  )}
                </div>
              </div>

              <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[11px] font-mono text-[#666666] flex justify-between items-center">
                <span>Version: {policy.version}</span>
                <span className="text-[10px] text-[#999999]">ID: {policy.id.substring(0, 8)}...</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
