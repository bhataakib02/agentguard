"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Shield,
  Filter,
  RefreshCw,
  PlusCircle,
  Building,
  CheckCircle,
  AlertTriangle,
  Lock,
  Eye,
  FileText
} from "lucide-react";

export default function PlatformGovernancePage() {
  const [policies, setPolicies] = useState<any[]>([]);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [selectedOrg, setSelectedOrg] = useState("ALL");
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [polData, orgData] = await Promise.all([
        fetchApi(`/platform/governance?org_id=${selectedOrg}`),
        fetchApi("/platform/organizations")
      ]);
      setPolicies(polData || []);
      setOrganizations(orgData || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedOrg]);

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Governance Policies</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              GLOBAL PLATFORM SCOPE
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Global governance policies and enforcement rules across all registered organizations.
          </p>
        </div>

        <button
          onClick={() => loadData()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-3.5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm text-[12px]">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-[#94A3B8]" />
          <span className="font-bold text-[#94A3B8]">Filter Organization:</span>
          <select
            value={selectedOrg}
            onChange={(e) => setSelectedOrg(e.target.value)}
            className="bg-[#161C2A] border border-[#232F48] text-white text-[12px] font-bold rounded-[6px] px-3 py-1.5 outline-none focus:border-[#2E9D50] cursor-pointer"
          >
            <option value="ALL">🌐 All Organizations (Global)</option>
            {organizations.map((o) => (
              <option key={o.id} value={o.id}>🏢 {o.name}</option>
            ))}
          </select>
        </div>

        <div className="text-[11px] font-mono text-[#64748B]">
          Showing <strong className="text-white">{policies.length}</strong> platform governance policies
        </div>
      </div>

      {/* Governance Policies Table */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase font-mono">
              <tr>
                <th className="py-3.5 px-4">Policy Name</th>
                <th className="py-3.5 px-4">Organization Scope</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-center">Rules Count</th>
                <th className="py-3.5 px-4">Enforcement Mode</th>
                <th className="py-3.5 px-4">Created</th>
                <th className="py-3.5 px-4">Updated</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {policies.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-[#64748B] font-mono">
                    No governance policies found matching current scope filter.
                  </td>
                </tr>
              ) : (
                policies.map((p) => (
                  <tr key={p.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-white text-[13px]">{p.name}</div>
                      <div className="text-[11px] text-[#64748B] line-clamp-1">{p.description || "Global compliance policy rule set."}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#161C2A] text-[#94A3B8] border border-[#232F48] font-mono">
                        {p.org_name}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                        p.status === "ACTIVE"
                          ? "bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40"
                          : "bg-[#161C2A] text-[#64748B] border border-[#232F48]"
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-bold text-white font-mono">
                      {p.rules_count ?? 3}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3B1516] text-[#E53935] border border-[#E53935]/40 font-mono">
                        {p.enforcement_mode}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[#64748B] text-[11px]">
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : "2026-08-15"}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[#64748B] text-[11px]">
                      {p.updated_at ? new Date(p.updated_at).toLocaleDateString() : "2026-09-02"}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => alert(`Policy Details:\n${p.name}\nScope: ${p.org_name}\nRules: ${p.rules_count}\nEnforcement: ${p.enforcement_mode}`)}
                        className="px-2.5 py-1 bg-[#161C2A] border border-[#232F48] text-[#94A3B8] hover:text-white rounded-[6px] text-[11px] font-bold transition-colors"
                      >
                        Inspect
                      </button>
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
