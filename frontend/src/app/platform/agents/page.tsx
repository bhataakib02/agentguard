"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { Bot, Search, RefreshCw, Shield, AlertTriangle } from "lucide-react";

export default function PlatformAgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadAgents = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/agents");
      setAgents(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const filtered = agents.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.agent_code.toLowerCase().includes(search.toLowerCase()) ||
    a.org_name.toLowerCase().includes(search.toLowerCase()) ||
    a.owner_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">Global AI Agent Directory</h1>
          <p className="text-[12px] text-[#64748B]">Governed machine AI employees across all tenant organizations</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 text-[#64748B] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search agents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[12px] text-white outline-none focus:border-[#2E9D50]"
            />
          </div>

          <button
            onClick={() => loadAgents()}
            className="p-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">
              <tr>
                <th className="py-3 px-4">Agent Code</th>
                <th className="py-3 px-4">Agent Name</th>
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Human Owner</th>
                <th className="py-3 px-4">IAM Role</th>
                <th className="py-3 px-4">Autonomy Tier</th>
                <th className="py-3 px-4">Risk Score</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-[#64748B]">
                    Loading AI agents from database...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-[#64748B]">
                    No AI agents found matching search filter.
                  </td>
                </tr>
              ) : (
                filtered.map((a) => (
                  <tr key={a.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-[#2E9D50]">{a.agent_code}</td>
                    <td className="py-3.5 px-4 font-bold text-white">{a.name}</td>
                    <td className="py-3.5 px-4 text-[#94A3B8]">{a.org_name}</td>
                    <td className="py-3.5 px-4 text-white font-medium">{a.owner_name}</td>
                    <td className="py-3.5 px-4 font-mono text-[10px] font-bold text-[#2E9D50]">AGENT</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] font-mono">
                        {a.autonomy_level}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-[#2E9D50]">{a.risk_score} / 100</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50]">
                        {a.status}
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
