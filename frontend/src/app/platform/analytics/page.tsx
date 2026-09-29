"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Activity,
  TrendingUp,
  RefreshCw,
  Zap,
  Users,
  Bot,
  BarChart3,
  Globe
} from "lucide-react";

export default function PlatformAnalyticsPage() {
  const [overview, setOverview] = useState<any>(null);
  const [apiData, setApiData] = useState<any>(null);
  const [timeSeries, setTimeSeries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const [ovData, apis, tsData] = await Promise.all([
        fetchApi("/platform/overview").catch(() => null),
        fetchApi("/platform/api").catch(() => null),
        fetchApi("/analytics/time-series?range=7d").catch(() => null)
      ]);
      setOverview(ovData);
      setApiData(apis);
      if (tsData && Array.isArray(tsData.data)) {
        setTimeSeries(tsData.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  const totalDecisions = timeSeries.reduce((acc, curr) => acc + (curr.decisions || 0), 0);
  const maxDecisions = Math.max(...timeSeries.map((d) => d.decisions || 0), 1);

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Usage & Telemetry Analytics</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              GLOBAL PLATFORM ANALYTICS
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Platform-wide throughput, authenticated user counts, decision execution volume, and live security telemetry.
          </p>
        </div>

        <button
          onClick={() => loadAnalytics()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">24h Evaluation Requests</span>
          <h2 className="text-[28px] font-bold text-white">
            {loading ? "Loading..." : (apiData?.api_gateways?.[0]?.requests_24h ?? "0")}
          </h2>
          <span className="text-[10px] text-[#94A3B8] font-bold">Live database telemetry</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Active Users</span>
          <h2 className="text-[28px] font-bold text-white">
            {loading ? "Loading..." : (overview?.total_users ?? 0)}
          </h2>
          <span className="text-[10px] text-[#2E9D50] font-bold">Registered platform users</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Governed AI Agents</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">
            {loading ? "Loading..." : (overview?.total_ai_agents ?? 0)}
          </h2>
          <span className="text-[10px] text-[#94A3B8] font-bold">Monitored agent instances</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Blocked / Refused</span>
          <h2 className="text-[28px] font-bold text-[#F87171]">
            {loading ? "Loading..." : (overview?.security_overview?.blocked_actions ?? 0)}
          </h2>
          <span className="text-[10px] text-[#94A3B8] font-bold">Enforced policy boundaries</span>
        </div>
      </div>

      {/* GRAPH PANEL */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#2E9D50]" />
            <span>Platform Decision Volume (Last 7 Days)</span>
          </h3>
          <span className="text-[11px] text-[#94A3B8] font-mono">
            {loading ? "Loading..." : `${totalDecisions} total events`}
          </span>
        </div>

        <div className="h-48 w-full bg-[#161C2A] rounded-[8px] border border-[#232F48] p-4 flex items-end justify-between gap-2">
          {loading ? (
            <div className="w-full h-full flex items-center justify-center text-[12px] text-[#64748B]">
              Loading telemetry...
            </div>
          ) : timeSeries.length === 0 ? (
            <div className="w-full h-full flex items-center justify-center text-[12px] text-[#64748B]">
              No decision telemetry recorded in this period.
            </div>
          ) : (
            timeSeries.map((point: any, idx: number) => {
              const heightPct = Math.max(8, Math.round(((point.decisions || 0) / maxDecisions) * 100));
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                  <span className="text-[10px] text-[#94A3B8] font-mono">{point.decisions || 0}</span>
                  <div
                    className="w-full bg-[#2E9D50] hover:bg-[#34B35B] rounded-t transition-all"
                    style={{ height: `${heightPct}%`, minHeight: "4px" }}
                    title={`${point.date}: ${point.decisions} decisions (${point.allowed} allowed, ${point.refused} refused)`}
                  />
                  <span className="text-[9px] text-[#64748B] font-mono truncate max-w-full">
                    {point.date ? point.date.slice(5) : idx}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
