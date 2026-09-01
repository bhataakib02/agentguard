"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import {
  Building,
  Search,
  PlusCircle,
  RefreshCw,
  CheckCircle,
  XCircle,
  Eye,
  Lock,
  CreditCard,
  Users,
  Bot
} from "lucide-react";

export default function PlatformOrganizationsPage() {
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadOrgs = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/organizations");
      setOrganizations(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrgs();
  }, []);

  const handleToggleStatus = async (orgId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
    try {
      await fetchApi(`/platform/organizations/${orgId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus })
      });
      loadOrgs();
    } catch (err: any) {
      alert("Status change failed: " + err.message);
    }
  };

  const filtered = organizations.filter((o) =>
    o.name.toLowerCase().includes(search.toLowerCase()) ||
    (o.domain || "").toLowerCase().includes(search.toLowerCase()) ||
    (o.admin_email || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">Organization Directory</h1>
          <p className="text-[12px] text-[#64748B]">Managed multi-tenant customer organizations across the platform</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 text-[#64748B] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search organizations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[12px] text-white outline-none focus:border-[#2E9D50]"
            />
          </div>

          <button
            onClick={() => loadOrgs()}
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
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Organization ID</th>
                <th className="py-3 px-4">Plan / License</th>
                <th className="py-3 px-4">Admin Contact</th>
                <th className="py-3 px-4 text-center">Users</th>
                <th className="py-3 px-4 text-center">AI Agents</th>
                <th className="py-3 px-4">Created Date</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-[#64748B]">
                    Loading organizations from Supabase database...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-[#64748B]">
                    No organizations found matching search criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((org) => (
                  <tr key={org.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3.5 px-4 font-bold text-white flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded bg-[#173B25] text-[#2E9D50] font-bold flex items-center justify-center text-[11px]">
                        {org.name[0]}
                      </div>
                      <span>{org.name}</span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-[#64748B]">{org.id.substring(0, 8)}...</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                        {org.plan_id}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[#94A3B8]">{org.admin_email}</td>
                    <td className="py-3.5 px-4 text-center font-bold text-white">{org.user_count} / {org.max_users}</td>
                    <td className="py-3.5 px-4 text-center font-bold text-white">{org.agent_count} / {org.max_ai_agents}</td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-[#94A3B8]">
                      {org.created_at ? new Date(org.created_at).toLocaleDateString() : "Aug 31, 2026"}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50]">
                        {org.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleToggleStatus(org.id, org.status)}
                        className="px-2.5 py-1 bg-[#161C2A] border border-[#232F48] rounded-[6px] text-[11px] font-bold text-[#E53935] hover:bg-[#3B1516]"
                      >
                        {org.status === "ACTIVE" ? "Suspend" : "Activate"}
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
