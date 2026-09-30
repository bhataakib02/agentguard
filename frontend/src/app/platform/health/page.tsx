"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Server,
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Clock,
  Zap,
  ShieldCheck,
  Database,
  Lock,
  Bell,
  Cpu
} from "lucide-react";

export default function PlatformHealthPage() {
  const [healthData, setHealthData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadHealth = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/health");
      setHealthData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  const services = healthData?.services || [];

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">System Health</h1>
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase font-mono flex items-center gap-1 ${
              healthData?.overall_status === "Operational"
                ? "bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40"
                : "bg-[#3D2910] text-[#F59A23] border border-[#F59A23]/40"
            }`}>
              <CheckCircle className="w-3 h-3" /> {loading ? "CHECKING HEALTH..." : (healthData?.overall_status || "OPERATIONAL").toUpperCase()}
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Real-time health, latency, live telemetry, and status of AgentGuard core subsystem services.
          </p>
        </div>

        <button
          onClick={() => loadHealth()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Check Status Now</span>
        </button>
      </div>

      {/* CORE SERVICE HEALTH CARDS */}
      {loading ? (
        <div className="p-8 text-center text-[#64748B] text-[13px] bg-[#121722] border border-[#1E2638] rounded-[12px]">
          Loading subsystem health and live database telemetry...
        </div>
      ) : services.length === 0 ? (
        <div className="p-8 text-center text-[#64748B] text-[13px] bg-[#121722] border border-[#1E2638] rounded-[12px]">
          No health telemetry available.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {services.map((srv: any) => (
            <div
              key={srv.id || srv.name}
              className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-3 shadow-sm hover:border-[#2E9D50]/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">{srv.category || "Core"}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                  srv.status === "Operational" || srv.status === "HEALTHY"
                    ? "bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40"
                    : srv.status === "Not Configured" || srv.status === "NOT_CONFIGURED"
                    ? "bg-[#281816] text-[#EF4444] border border-[#EF4444]/40"
                    : "bg-[#3D2910] text-[#F59A23] border border-[#F59A23]/40"
                }`}>
                  {srv.status}
                </span>
              </div>

              <h3 className="font-bold text-white text-[15px]">{srv.name}</h3>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#1E2638] text-[11px] font-mono">
                <div>
                  <span className="text-[#64748B] block">Telemetry</span>
                  <span className="text-white font-bold">{srv.telemetry || "Active"}</span>
                </div>
                <div>
                  <span className="text-[#64748B] block">Response</span>
                  <span className="text-[#2E9D50] font-bold">
                    {srv.latency_ms !== null && srv.latency_ms !== undefined ? `${srv.latency_ms} ms` : "N/A"}
                  </span>
                </div>
                <div>
                  <span className="text-[#64748B] block">Checked</span>
                  <span className="text-white font-bold">Just now</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* RECENT SYSTEM EVENTS LOG */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#2E9D50]" />
          <span>Recent System Operational Events</span>
        </h3>

        <div className="space-y-2 text-[12px]">
          {(healthData?.recent_system_events && healthData.recent_system_events.length > 0) ? (
            healthData.recent_system_events.map((evt: any, idx: number) => (
              <div key={idx} className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between font-mono">
                <div className="flex items-center gap-3">
                  <span className="text-[#64748B] text-[11px]">{evt.time}</span>
                  <span className="font-bold text-white text-[12px]">{evt.event}</span>
                </div>
                <span className="text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] px-2 py-0.5 rounded border border-[#2E9D50]/30">
                  {evt.source}
                </span>
              </div>
            ))
          ) : (
            <div className="p-4 text-center text-[#64748B] text-[12px] font-mono">
              No recent operational events recorded.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
