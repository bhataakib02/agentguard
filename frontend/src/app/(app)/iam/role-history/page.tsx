"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { Shield, Clock, ArrowRight, UserCheck } from "lucide-react";

export default function RoleHistoryPage() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRoleHistory() {
      try {
        setLoading(true);
        const data = await fetchApi("/audit/logs?event_type=ROLE_CHANGED").catch(() => []);
        setHistory(data || []);
      } catch (err) {
        console.error("Role history fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadRoleHistory();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">IAM Role Assignment History</h1>
        <p className="text-[13px] text-[#666666]">
          Immutable Audit Log Records for All Historical Organization Role Changes
        </p>
      </div>

      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm p-4 space-y-3">
        <h3 className="text-[16px] font-bold text-[#1F1F1F] px-2">Role Modification Records</h3>

        {history.length === 0 ? (
          <div className="p-8 text-center space-y-2">
            <Clock className="w-8 h-8 text-[#666666] mx-auto opacity-40" />
            <p className="text-[13px] text-[#666666]">Zero role modification audit records found in PostgreSQL.</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-3">TIMESTAMP</th>
                <th className="p-3">ACTOR ADMIN</th>
                <th className="p-3">TARGET USER</th>
                <th className="p-3">ROLE TRANSITION</th>
                <th className="p-3">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {history.map((h) => {
                const meta = h.metadata_json || {};
                return (
                  <tr key={h.id} className="hover:bg-[#FCFCFA]">
                    <td className="p-3 text-[#666666] text-[12px]">
                      {new Date(h.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3 font-bold text-[#1F1F1F]">
                      {meta.actor_user_id || h.actor_id}
                    </td>
                    <td className="p-3 font-bold text-[#1F1F1F]">
                      {meta.target_user_id || h.resource}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2 font-bold text-[12px]">
                        <span className="px-2 py-0.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded text-[#666666]">
                          {meta.previous_role || "USER"}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-[#2E9D50]" />
                        <span className="px-2 py-0.5 bg-[#F1EDFA] border border-[#8064C8]/30 rounded text-[#8064C8]">
                          {meta.new_role || "MANAGER"}
                        </span>
                      </div>
                    </td>
                    <td className="p-3">
                      <span className="text-[11px] font-bold text-[#237A3C] bg-[#EAF7EE] px-2 py-0.5 rounded">
                        {h.result || "SUCCESS"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
