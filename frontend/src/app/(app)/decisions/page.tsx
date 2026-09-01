"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Shield, GitFork } from "lucide-react";

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDecisions() {
      try {
        const data = await fetchApi("/decisions").catch(() => []);
        setDecisions(data || []);
      } catch (err) {
        console.error("Decisions fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadDecisions();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Decision Black Box Stream</h1>
        <p className="text-[13px] text-[#666666]">
          Immutable Log of Governance Decisions & Intent Evaluation Records
        </p>
      </div>

      {decisions.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Shield className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Decisions Recorded</h3>
          <p className="text-[12px] text-[#666666]">
            No governance decisions exist in the database. Use the Evaluator on the Dashboard to execute actions.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-x-auto shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">ACTION</th>
                <th className="p-4">RESOURCE TARGET</th>
                <th className="p-4">AMOUNT</th>
                <th className="p-4">DECISION</th>
                <th className="p-4">POLICY APPLIED</th>
                <th className="p-4 text-right">PROVENANCE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {decisions.map((dec) => (
                <tr key={dec.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-bold text-[#1F1F1F]">{dec.action_requested}</td>
                  <td className="p-4 text-[#666666]">{dec.resource_target}</td>
                  <td className="p-4 font-bold text-[#2E9D50]">₹{dec.amount ? dec.amount.toLocaleString() : "0"}.00</td>
                  <td className="p-4"><StatusBadge status={dec.decision} /></td>
                  <td className="p-4 text-[12px] text-[#666666]">{dec.policy_name}</td>
                  <td className="p-4 text-right">
                    <Link
                      href={`/provenance?id=${dec.id}`}
                      className="inline-flex items-center gap-1 text-[12px] font-bold text-[#8064C8] hover:underline"
                    >
                      <GitFork className="w-3.5 h-3.5" />
                      <span>Trace</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
