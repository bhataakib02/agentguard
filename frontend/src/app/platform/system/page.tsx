"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { Server, RefreshCw, CheckCircle, Activity, Database, Cpu } from "lucide-react";

export default function PlatformSystemPage() {
  const [sysData, setSysData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadSystem = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/system");
      setSysData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSystem();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#1E2638] pb-4">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">System Infrastructure Health</h1>
          <p className="text-[12px] text-[#64748B]">Real-time operational status, latencies, and uptime across backend, database, and authentication engines</p>
        </div>

        <button
          onClick={() => loadSystem()}
          className="p-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Health</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {(sysData?.services || []).map((srv: any, idx: number) => (
          <div key={idx} className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-3 h-3 rounded-full bg-[#2E9D50] animate-pulse" />
                <h3 className="font-bold text-white text-[15px]">{srv.name}</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] font-mono">
                {srv.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[#1E2638] text-[12px]">
              <div>
                <span className="text-[#64748B] block text-[10px] uppercase font-mono">Uptime</span>
                <span className="font-bold text-white font-mono">{srv.uptime}</span>
              </div>
              <div>
                <span className="text-[#64748B] block text-[10px] uppercase font-mono">Latency</span>
                <span className="font-bold text-[#2E9D50] font-mono">{srv.latency_ms} ms</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
