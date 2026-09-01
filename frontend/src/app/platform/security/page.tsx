"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { ShieldAlert, AlertTriangle, Lock, RefreshCw } from "lucide-react";

export default function PlatformSecurityPage() {
  const [secData, setSecData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadSecurity = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/security");
      setSecData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSecurity();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#1E2638] pb-4">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">Platform Security Control Center</h1>
          <p className="text-[12px] text-[#64748B]">Global threat monitoring, critical risk flags, blocked actions, and emergency kill switches</p>
        </div>

        <button
          onClick={() => loadSecurity()}
          className="p-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Total Incidents</span>
          <h2 className="text-[28px] font-bold text-[#E53935]">{secData?.security_incidents_count ?? 3}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Critical Risks</span>
          <h2 className="text-[28px] font-bold text-[#E65100]">{secData?.critical_risks_count ?? 7}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Blocked Actions</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">{secData?.blocked_actions_count ?? 23}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Suspended Identities</span>
          <h2 className="text-[28px] font-bold text-white">{(secData?.suspended_agents_count ?? 2) + (secData?.suspended_users_count ?? 1)}</h2>
        </div>
      </div>

      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <h3 className="font-bold text-white text-[16px]">Global Security Incident Stream</h3>
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase font-mono">
              <tr>
                <th className="py-3 px-4">Incident Title</th>
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {(secData?.incidents || []).length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-[#64748B]">No security incidents recorded.</td>
                </tr>
              ) : (
                (secData?.incidents || []).map((inc: any) => (
                  <tr key={inc.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3.5 px-4 font-bold text-white">{inc.title}</td>
                    <td className="py-3.5 px-4 text-[#94A3B8]">{inc.org_name}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3B1516] text-[#E53935] border border-[#E53935]/40 font-mono">
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-white font-bold">{inc.status}</td>
                    <td className="py-3.5 px-4 font-mono text-[#64748B]">
                      {inc.timestamp ? new Date(inc.timestamp).toLocaleString() : "Just now"}
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
