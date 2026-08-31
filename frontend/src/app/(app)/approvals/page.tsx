"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { UserCheck, Check, X } from "lucide-react";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadApprovals = async () => {
    try {
      setLoading(true);
      const data = await fetchApi("/approvals").catch(() => []);
      setApprovals(data || []);
    } catch (err) {
      console.error("Approvals fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const handleAct = async (approvalId: string, action: "APPROVE" | "REJECT") => {
    try {
      await fetchApi(`/approvals/${approvalId}/act`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      await loadApprovals();
    } catch (err: any) {
      alert(`Action error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Human Approval Queue</h1>
        <p className="text-[13px] text-[#666666]">
          Managerial Review & Human-in-the-Loop Governance Escalation Queue
        </p>
      </div>

      {approvals.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <UserCheck className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Pending Approvals</h3>
          <p className="text-[12px] text-[#666666]">
            No governance decisions currently require human approval.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">AGENT</th>
                <th className="p-4">ACTION</th>
                <th className="p-4">AMOUNT</th>
                <th className="p-4">ESCALATION REASON</th>
                <th className="p-4">STATUS</th>
                <th className="p-4 text-right">MANAGERIAL ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {approvals.map((app) => (
                <tr key={app.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4">
                    <span className="font-bold text-[#1F1F1F] block">{app.agent_name}</span>
                    <span className="text-[11px] font-bold text-[#8064C8]">{app.agent_code}</span>
                  </td>
                  <td className="p-4 font-bold text-[#1F1F1F]">{app.action}</td>
                  <td className="p-4 font-bold text-[#2E9D50]">₹{app.amount ? app.amount.toLocaleString() : "0"}.00</td>
                  <td className="p-4 text-[12px] text-[#666666]">{app.reason}</td>
                  <td className="p-4"><StatusBadge status={app.status} /></td>
                  <td className="p-4 text-right space-x-2">
                    {app.status === "PENDING" ? (
                      <>
                        <button
                          onClick={() => handleAct(app.id, "APPROVE")}
                          className="px-3 py-1 bg-[#2E9D50] text-white rounded-[6px] text-[11px] font-bold hover:bg-[#237A3C]"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleAct(app.id, "REJECT")}
                          className="px-3 py-1 bg-[#E53935] text-white rounded-[6px] text-[11px] font-bold hover:bg-[#C62828]"
                        >
                          Reject
                        </button>
                      </>
                    ) : (
                      <span className="text-[11px] text-[#666666] font-bold">Resolved</span>
                    )}
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
