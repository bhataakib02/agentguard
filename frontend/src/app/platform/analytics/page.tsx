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
  const [loading, setLoading] = useState(true);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/overview");
      setOverview(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

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
            Platform-wide API throughput, user telemetry, decision volume, and storage utilization.
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
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">API Request Volume</span>
          <h2 className="text-[28px] font-bold text-white">1.42M</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold">↑ 14% vs last 30d</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Active User Telemetry</span>
          <h2 className="text-[28px] font-bold text-white">{overview?.total_users ?? 40}</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold">100% active sessions</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Agent Decision Volume</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">{overview?.audit_events ?? 1248}</h2>
          <span className="text-[10px] text-[#2E9D50] font-bold">↑ 18% vs last 30d</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Storage Consumption</span>
          <h2 className="text-[28px] font-bold text-white">24.5 GB</h2>
          <span className="text-[10px] text-[#94A3B8] font-bold">12.2% of total allocated</span>
        </div>
      </div>

      {/* GRAPH PANEL */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#2E9D50]" />
          <span>Platform Execution Telemetry Graph</span>
        </h3>

        <div className="h-64 w-full relative pt-4 pb-2 bg-[#161C2A] rounded-[8px] border border-[#232F48] p-4">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 500 140" preserveAspectRatio="none">
            <line x1="0" y1="25" x2="500" y2="25" stroke="#1E2638" strokeDasharray="3 3" />
            <line x1="0" y1="65" x2="500" y2="65" stroke="#1E2638" strokeDasharray="3 3" />
            <line x1="0" y1="105" x2="500" y2="105" stroke="#1E2638" strokeDasharray="3 3" />

            <path
              d="M 0 110 L 50 90 L 100 70 L 150 80 L 200 40 L 250 55 L 300 45 L 350 70 L 400 30 L 450 40 L 500 25"
              fill="none"
              stroke="#2E9D50"
              strokeWidth="3"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}
