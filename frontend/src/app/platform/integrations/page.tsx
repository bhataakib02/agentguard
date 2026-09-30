"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Layers,
  CheckCircle,
  AlertCircle,
  XCircle,
  RefreshCw,
  Server,
  Database,
  Lock,
  Radio,
  Sparkles,
  CreditCard,
  Cloud,
  MessageSquare,
  Mail,
  ShieldCheck
} from "lucide-react";

export default function PlatformIntegrationsHubPage() {
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadIntegrations = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/integrations");
      setIntegrations(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIntegrations();
  }, []);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "Database":
        return <Database className="w-4 h-4 text-[#2E9D50]" />;
      case "Identity Provider":
        return <Lock className="w-4 h-4 text-[#8064C8]" />;
      case "Notifications & Dispatch":
        return <Radio className="w-4 h-4 text-[#2E9D50]" />;
      case "LLM Provider":
        return <Sparkles className="w-4 h-4 text-[#8064C8]" />;
      case "Payment Gateway":
      case "Payment API":
        return <CreditCard className="w-4 h-4 text-[#F59A23]" />;
      case "Cloud Infrastructure":
        return <Cloud className="w-4 h-4 text-[#64748B]" />;
      case "Team Collaboration":
        return <MessageSquare className="w-4 h-4 text-[#F59A23]" />;
      case "Email & Notifications":
        return <Mail className="w-4 h-4 text-[#F59A23]" />;
      default:
        return <Layers className="w-4 h-4 text-[#64748B]" />;
    }
  };

  const getStatusBadge = (status: string, classification: string) => {
    if (status === "CONNECTED") {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
          CONNECTED
        </span>
      );
    }
    if (status === "CONFIGURED") {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#162238] text-[#60A5FA] border border-[#60A5FA]/40 font-mono">
          CONFIGURED (ENV)
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#281816] text-[#EF4444] border border-[#EF4444]/40 font-mono">
        NOT CONFIGURED
      </span>
    );
  };

  const connectedCount = integrations.filter((i) => i.status === "CONNECTED").length;
  const configuredCount = integrations.filter((i) => i.status === "CONFIGURED").length;
  const unconfiguredCount = integrations.filter((i) => i.status === "NOT_CONFIGURED").length;

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Integrations Hub</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#162238] text-[#60A5FA] border border-[#60A5FA]/40 font-mono">
              TRUTHFUL VERIFICATION
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Operational status and environment configuration for databases, LLM providers, payment gateways, and messaging services.
          </p>
        </div>

        <button
          onClick={() => loadIntegrations()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Verify Providers</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Live Connected</span>
          <h2 className="text-[28px] font-bold text-[#2E9D50]">{loading ? "..." : connectedCount}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Environment Configured</span>
          <h2 className="text-[28px] font-bold text-[#60A5FA]">{loading ? "..." : configuredCount}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Unconfigured Providers</span>
          <h2 className="text-[28px] font-bold text-[#EF4444]">{loading ? "..." : unconfiguredCount}</h2>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Total Supported</span>
          <h2 className="text-[28px] font-bold text-white">{loading ? "..." : integrations.length}</h2>
        </div>
      </div>

      {/* Integrity Notice Banner */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 text-[12px] text-[#94A3B8] flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-[#2E9D50] shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-white block">Zero Deceptive Status Policy</span>
          Integrations are strictly verified against actual environment configuration and live network probes.
          Services lacking configured credentials are never labeled as CONNECTED or Operational. Plaintext API secrets are never returned in dashboard responses.
        </div>
      </div>

      {/* Provider Cards Grid */}
      {loading ? (
        <div className="p-12 text-center text-[#64748B] text-[13px] bg-[#121722] border border-[#1E2638] rounded-[12px]">
          Probing and verifying provider configurations...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {integrations.map((item: any) => (
            <div
              key={item.id}
              className={`bg-[#121722] border rounded-[12px] p-5 space-y-3 shadow-sm transition-colors ${
                item.status === "CONNECTED"
                  ? "border-[#2E9D50]/40 hover:border-[#2E9D50]"
                  : item.status === "CONFIGURED"
                  ? "border-[#60A5FA]/40 hover:border-[#60A5FA]"
                  : "border-[#1E2638] hover:border-[#232F48]"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono flex items-center gap-1.5">
                  {getCategoryIcon(item.category)}
                  <span>{item.category}</span>
                </span>
                {getStatusBadge(item.status, item.classification)}
              </div>

              <div>
                <h3 className="font-bold text-white text-[15px]">{item.name}</h3>
                <span className="text-[10px] font-mono text-[#64748B] block mt-0.5 uppercase">
                  CLASSIFICATION: {item.classification || "CONFIGURED"}
                </span>
              </div>

              <p className="text-[12px] text-[#94A3B8] bg-[#161C2A] p-2.5 rounded-[6px] border border-[#232F48] leading-relaxed">
                {item.details}
              </p>

              <div className="flex items-center justify-between text-[11px] font-mono text-[#64748B] pt-1">
                <span>Health: <strong className={item.health === "HEALTHY" ? "text-[#2E9D50]" : "text-[#94A3B8]"}>{item.health}</strong></span>
                <span>ID: {item.id}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
