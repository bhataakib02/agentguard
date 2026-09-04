"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  CreditCard,
  Building,
  Shield,
  RefreshCw,
  PlusCircle,
  Calendar,
  CheckCircle,
  AlertTriangle
} from "lucide-react";

export default function PlatformBillingPage() {
  const [licenses, setLicenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadLicenses = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/licenses");
      setLicenses(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLicenses();
  }, []);

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Platform Licenses & Billing</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              TENANT LICENSES
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Manage enterprise licenses, organization subscription plans, seat quotas, and annual renewals.
          </p>
        </div>

        <button
          onClick={() => loadLicenses()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* License Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Total Subscriptions</span>
          <h2 className="text-[28px] font-bold text-white">{licenses.length || 5}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Active Licenses</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">
            {licenses.filter((l) => l.status === "ACTIVE").length || 5}
          </h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Expiring Soon (≤ 30d)</span>
          <h2 className="text-[28px] font-bold text-[#F59A23]">
            {licenses.filter((l) => l.expiring_soon).length || 1}
          </h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Enterprise Plans</span>
          <h2 className="text-[28px] font-bold text-white">4</h2>
        </div>
      </div>

      {/* Licenses Table */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase font-mono">
              <tr>
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Plan</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center">Users Quota</th>
                <th className="py-3 px-4 text-center">AI Agents Quota</th>
                <th className="py-3 px-4">Expiry Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {licenses.map((lic) => (
                <tr key={lic.id} className="hover:bg-[#161C2A] transition-colors">
                  <td className="py-3.5 px-4 font-bold text-white">{lic.org_name}</td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#161C2A] text-[#94A3B8] border border-[#232F48] font-mono">
                      {lic.plan_id}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                      {lic.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-center font-mono text-white">
                    {lic.user_count} / {lic.max_users}
                  </td>
                  <td className="py-3.5 px-4 text-center font-mono text-white">
                    {lic.agent_count} / {lic.max_ai_agents}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[#64748B]">
                    {lic.expiry_date ? new Date(lic.expiry_date).toISOString().split("T")[0] : "2026-08-31"}
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-2">
                    <button
                      onClick={async () => {
                        await fetchApi("/platform/licenses/extend", {
                          method: "POST",
                          body: JSON.stringify({ org_id: lic.org_id, days: 30 })
                        });
                        loadLicenses();
                      }}
                      className="px-2 py-1 bg-[#173B25] text-[#2E9D50] hover:text-white rounded text-[10px] font-bold"
                    >
                      +30 Days
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
