"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Flame, ShieldAlert } from "lucide-react";

export default function RuntimePage() {
  const [cbs, setCbs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadCbs = async () => {
    try {
      setLoading(true);
      const data = await fetchApi("/runtime/circuit-breakers").catch(() => []);
      setCbs(data || []);
    } catch (err) {
      console.error("Runtime fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCbs();
  }, []);

  const handleToggle = async (agentId: string, currentState: string) => {
    try {
      const endpoint = currentState === "SUSPENDED" ? `/agents/${agentId}/restore` : `/agents/${agentId}/suspend`;
      await fetchApi(endpoint, { method: "POST" });
      await loadCbs();
    } catch (err: any) {
      alert(`Toggle error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Circuit Breaker & Kill Switch</h1>
        <p className="text-[13px] text-[#666666]">
          Emergency Manual Suspension State Machine & Automated Tripping Control
        </p>
      </div>

      {cbs.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Flame className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Circuit Breakers Configured</h3>
          <p className="text-[12px] text-[#666666]">
            No agent circuit breakers exist in the database. Register an agent in the directory to initialize circuit breakers.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-x-auto shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">AI AGENT</th>
                <th className="p-4">STATE MACHINE</th>
                <th className="p-4">TRIGGER REASON</th>
                <th className="p-4 text-right">MANUAL KILL SWITCH</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {cbs.map((cb) => (
                <tr key={cb.agent_id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4">
                    <span className="font-bold text-[#1F1F1F] block">{cb.name}</span>
                    <span className="text-[11px] font-bold text-[#8064C8]">{cb.agent_code}</span>
                  </td>
                  <td className="p-4"><StatusBadge status={cb.state} /></td>
                  <td className="p-4 text-[12px] text-[#666666]">{cb.trigger_reason || "Normal Autonomous Operations"}</td>
                  <td className="p-4 text-right">
                    <button
                      onClick={() => handleToggle(cb.agent_id, cb.state)}
                      className={`px-3 py-1.5 rounded-[6px] text-[11px] font-bold transition-colors ${
                        cb.state === "SUSPENDED"
                          ? "bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30"
                          : "bg-[#FDECEC] text-[#C62828] border border-[#E53935]/30"
                      }`}
                    >
                      {cb.state === "SUSPENDED" ? "Restore Agent" : "TRIP KILL SWITCH"}
                    </button>
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
