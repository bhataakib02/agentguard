"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { FileSearch, Search, RefreshCw } from "lucide-react";

export default function PlatformAuditPage() {
  const [audits, setAudits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadAudit = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/audit");
      setAudits(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const filtered = audits.filter((a) =>
    (a.action || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.actor || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.organization || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.target || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">Global Platform Audit Log Stream</h1>
          <p className="text-[12px] text-[#64748B]">Immutable audit trail of administrative actions, user changes, and agent deployments</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 text-[#64748B] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search audit trail..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[12px] text-white outline-none focus:border-[#2E9D50]"
            />
          </div>

          <button
            onClick={() => loadAudit()}
            className="p-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase font-mono">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Actor Type</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Target Resource</th>
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[#64748B]">Loading audit logs...</td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[#64748B]">No audit logs found matching query.</td>
                </tr>
              ) : (
                filtered.map((a) => (
                  <tr key={a.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3.5 px-4 font-mono text-[11px] text-[#94A3B8]">
                      {a.timestamp ? new Date(a.timestamp).toLocaleString() : "Just now"}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-[#2E9D50]">{a.actor}</td>
                    <td className="py-3.5 px-4 font-bold text-white">{a.action}</td>
                    <td className="py-3.5 px-4 text-[#94A3B8] font-mono">{a.target}</td>
                    <td className="py-3.5 px-4 text-[#2E9D50]">{a.organization}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50]">
                        {a.result}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
