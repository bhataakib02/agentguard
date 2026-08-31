"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { FileSearch } from "lucide-react";

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadLogs() {
      try {
        const data = await fetchApi("/audit/logs").catch(() => []);
        setLogs(data || []);
      } catch (err) {
        console.error("Audit fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Global Audit Trail</h1>
        <p className="text-[13px] text-[#666666]">
          Immutable Operational Log & Compliance History
        </p>
      </div>

      {logs.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <FileSearch className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Audit Logs Recorded</h3>
          <p className="text-[12px] text-[#666666]">
            No audit log entries exist in the database.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">EVENT TYPE</th>
                <th className="p-4">ACTOR</th>
                <th className="p-4">ACTION</th>
                <th className="p-4">RESOURCE</th>
                <th className="p-4">RESULT</th>
                <th className="p-4 text-right">TIMESTAMP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-bold text-[#1F1F1F]">{log.event_type}</td>
                  <td className="p-4 text-[#8064C8] font-bold">{log.actor_id}</td>
                  <td className="p-4 text-[#1F1F1F]">{log.action}</td>
                  <td className="p-4 text-[#666666]">{log.resource}</td>
                  <td className="p-4"><StatusBadge status={log.result} /></td>
                  <td className="p-4 text-right text-[11px] text-[#666666]">
                    {new Date(log.timestamp).toLocaleString()}
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
