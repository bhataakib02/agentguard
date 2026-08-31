"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { ShieldCheck, Lock } from "lucide-react";

export default function PermissionsPage() {
  const [matrix, setMatrix] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadMatrix() {
      try {
        const data = await fetchApi("/permissions/matrix").catch(() => []);
        setMatrix(data || []);
      } catch (err) {
        console.error("Permissions fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadMatrix();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Agent Permission Matrix</h1>
        <p className="text-[13px] text-[#666666]">
          Zero-Trust Scoped Resource Access Control & Permission Bounds
        </p>
      </div>

      {matrix.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Lock className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Permissions Configured</h3>
          <p className="text-[12px] text-[#666666]">
            No permission matrix entries exist in the database. Register an agent to view permission scoping.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">AI AGENT</th>
                <th className="p-4">DEPARTMENT</th>
                <th className="p-4">SCOPED PERMISSIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {matrix.map((row) => (
                <tr key={row.agent_id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4">
                    <span className="font-bold text-[#1F1F1F] block">{row.name}</span>
                    <span className="text-[11px] font-bold text-[#8064C8]">{row.agent_code}</span>
                  </td>
                  <td className="p-4 text-[#666666]">{row.department}</td>
                  <td className="p-4">
                    <div className="flex flex-wrap gap-2">
                      {Object.keys(row.permissions).length === 0 ? (
                        <span className="text-[11px] text-[#666666] italic">Default Autonomous Boundary</span>
                      ) : (
                        Object.entries(row.permissions).map(([resName, action]: any) => (
                          <span
                            key={resName}
                            className="px-2.5 py-1 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[11px] font-bold text-[#1F1F1F]"
                          >
                            {resName}: <span className="text-[#2E9D50]">{action}</span>
                          </span>
                        ))
                      )}
                    </div>
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
