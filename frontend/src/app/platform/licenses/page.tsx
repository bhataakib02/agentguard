"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { CreditCard, RefreshCw, Calendar, AlertTriangle, CheckCircle } from "lucide-react";

export default function PlatformLicensesPage() {
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

  const handleExtend = async (orgId: string) => {
    try {
      await fetchApi("/platform/licenses/extend", {
        method: "POST",
        body: JSON.stringify({ org_id: orgId, days: 30 })
      });
      loadLicenses();
    } catch (err: any) {
      alert("Extension failed: " + err.message);
    }
  };

  const handleRenew = async (orgId: string) => {
    try {
      await fetchApi("/platform/licenses/renew", {
        method: "POST",
        body: JSON.stringify({ org_id: orgId })
      });
      loadLicenses();
    } catch (err: any) {
      alert("Renewal failed: " + err.message);
    }
  };

  const handleRevoke = async (orgId: string) => {
    if (!confirm("Are you sure you want to revoke this license?")) return;
    try {
      await fetchApi("/platform/licenses/revoke", {
        method: "POST",
        body: JSON.stringify({ org_id: orgId, reason: "Administrative Revocation" })
      });
      loadLicenses();
    } catch (err: any) {
      alert("Revocation failed: " + err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#1E2638] pb-4">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">SaaS License & Expiration Center</h1>
          <p className="text-[12px] text-[#64748B]">Manage tenant subscription plans, annual renewals, seat caps, and expiration status</p>
        </div>

        <button
          onClick={() => loadLicenses()}
          className="p-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">
              <tr>
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Subscription Plan</th>
                <th className="py-3 px-4 text-center">User Seats</th>
                <th className="py-3 px-4 text-center">Agent Limit</th>
                <th className="py-3 px-4">Expiry Date</th>
                <th className="py-3 px-4">Days Remaining</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-[#64748B]">
                    Loading platform licenses...
                  </td>
                </tr>
              ) : licenses.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-[#64748B]">
                    No licenses found.
                  </td>
                </tr>
              ) : (
                licenses.map((lic) => (
                  <tr key={lic.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3.5 px-4 font-bold text-white">{lic.org_name}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                        {lic.plan_id}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-bold text-white">{lic.user_count} / {lic.max_users}</td>
                    <td className="py-3.5 px-4 text-center font-bold text-white">{lic.agent_count} / {lic.max_ai_agents}</td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-[#94A3B8]">
                      {lic.expiry_date ? new Date(lic.expiry_date).toLocaleDateString() : "Lifetime"}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-[#E65100]">
                      {lic.days_remaining != null ? `${lic.days_remaining} days` : "N/A"}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50]">
                        {lic.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleExtend(lic.org_id)}
                        className="px-2.5 py-1 bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 rounded-[6px] text-[11px] font-bold hover:bg-[#2E9D50] hover:text-white"
                      >
                        Extend 30d
                      </button>
                      <button
                        onClick={() => handleRenew(lic.org_id)}
                        className="px-2.5 py-1 bg-[#161C2A] border border-[#232F48] text-[#0284C7] rounded-[6px] text-[11px] font-bold hover:bg-[#1A2234]"
                      >
                        Renew 1Yr
                      </button>
                      <button
                        onClick={() => handleRevoke(lic.org_id)}
                        className="px-2.5 py-1 bg-[#161C2A] border border-[#232F48] text-[#E53935] rounded-[6px] text-[11px] font-bold hover:bg-[#3B1516]"
                      >
                        Revoke
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
