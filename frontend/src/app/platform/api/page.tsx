"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Cpu,
  Key,
  Globe,
  Radio,
  CheckCircle,
  ShieldCheck,
  RefreshCw,
  Copy,
  Plus,
  Server,
  Lock,
  Zap,
  Activity
} from "lucide-react";

export default function PlatformApiIntegrationsPage() {
  const [apiData, setApiData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadApiData = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/api");
      setApiData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApiData();
  }, []);

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Platform API & Integrations</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              PLATFORM SCOPE
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Global API management, webhooks, authentication, and external platform integrations.
          </p>
        </div>

        <button
          onClick={() => loadApiData()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Gateway Status</span>
          <h2 className="text-[24px] font-bold text-[#2E9D50] flex items-center gap-2">
            <CheckCircle className="w-5 h-5" /> {loading ? "Loading..." : (apiData?.api_status || "Operational")}
          </h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Total Platform Keys</span>
          <h2 className="text-[28px] font-bold text-white">{loading ? "Loading..." : (apiData?.total_api_keys ?? 0)}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Active Webhooks</span>
          <h2 className="text-[28px] font-bold text-white">{loading ? "Loading..." : (apiData?.active_webhooks ?? 0)}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Delivery Success Rate</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">{loading ? "Loading..." : (apiData?.webhook_delivery_rate || "No data available")}</h2>
        </div>
      </div>

      {/* SECTIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left 7 Cols: API Gateway & Connected Services */}
        <div className="lg:col-span-7 space-y-5">
          {/* API Gateways */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
            <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#2E9D50]" />
              <span>Platform Gateways</span>
            </h3>

            <div className="space-y-3 text-[12px]">
              {(apiData?.api_gateways || []).map((gw: any, idx: number) => (
                <div key={idx} className="p-3.5 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between">
                  <div>
                    <span className="font-bold text-white block">{gw.name}</span>
                    <span className="text-[11px] text-[#64748B] font-mono">
                      {gw.requests_24h ? `Requests (24h): ${gw.requests_24h}` : `Latency: ${gw.latency || "Live"}`} • Error Rate: {gw.error_rate || "0.00%"}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
                    {gw.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Connected Services */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
            <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
              <Server className="w-4 h-4 text-[#2E9D50]" />
              <span>Connected Infrastructure Services</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12px]">
              {(apiData?.connected_services || []).map((srv: any, idx: number) => (
                <div key={idx} className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-[13px]">{srv.name}</span>
                    <span className="text-[9px] font-bold uppercase bg-[#173B25] text-[#2E9D50] px-1.5 py-0.5 rounded font-mono">
                      {srv.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#64748B] font-mono flex justify-between">
                    <span>{srv.type}</span>
                    <span>Sync: {srv.last_sync}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right 5 Cols: Platform Key Management & Auth Config */}
        <div className="lg:col-span-5 space-y-5">
          {/* Super Admin API Key Management */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#1E2638] pb-3">
              <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
                <Key className="w-4 h-4 text-[#2E9D50]" />
                <span>Platform API Credentials</span>
              </h3>
              <span className="text-[10px] font-mono text-[#2E9D50] uppercase font-bold">ZERO-TRUST POLICY</span>
            </div>

            <div className="space-y-3 text-[12px]">
              <p className="text-[#94A3B8]">
                In accordance with enterprise zero-trust security standards, plaintext API secrets are never stored in the database or exposed in frontend dashboard responses.
              </p>

              <div className="p-3.5 bg-[#161C2A] rounded-[8px] border border-[#232F48] space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-[#94A3B8]">Credential Storage</span>
                  <span className="text-[#2E9D50] font-bold">Argon2 / SHA-256 Hashed</span>
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-[#94A3B8]">Secret Display</span>
                  <span className="text-white font-bold">One-Time On Generation</span>
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-[#94A3B8]">Active Keys</span>
                  <span className="text-white font-bold">{apiData?.total_api_keys ?? 0} Keys Provisioned</span>
                </div>
              </div>

              <div className="text-[11px] text-[#64748B] font-mono">
                Scope: <strong className="text-white">PLATFORM CONTROL PLANE</strong> • Tenant isolation strictly enforced
              </div>
            </div>
          </div>

          {/* Authentication Configuration */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-3 shadow-sm">
            <h3 className="font-bold text-white text-[15px] flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#2E9D50]" />
              <span>Authentication Engine Config</span>
            </h3>

            <div className="space-y-2 text-[12px]">
              <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[6px]">
                <span className="text-[#94A3B8]">Primary Auth Provider</span>
                <span className="font-bold text-white font-mono">Supabase Auth (OAuth2/JWT)</span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[6px]">
                <span className="text-[#94A3B8]">JWT Algorithm</span>
                <span className="font-bold text-[#2E9D50] font-mono">HS256 (Local) + RS256</span>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[6px]">
                <span className="text-[#94A3B8]">Session Expiry</span>
                <span className="font-bold text-white font-mono">480 Minutes (8 Hours)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
