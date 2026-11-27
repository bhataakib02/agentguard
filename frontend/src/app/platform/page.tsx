"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import {
  Building,
  Users,
  Bot,
  CreditCard,
  Key,
  ShieldAlert,
  TrendingUp,
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Eye,
  RefreshCw,
  PlusCircle,
  FileText,
  FileSearch,
  Server,
  Settings,
  ArrowUpRight,
  ExternalLink,
  Zap,
  Lock,
  Flame,
  Shield,
  Download,
  Calendar,
  ChevronDown,
  UserPlus,
  KeyRound,
  FileSpreadsheet
} from "lucide-react";

export default function PlatformDashboardPage() {
  const [overview, setOverview] = useState<any>(null);
  const [analyticsOverview, setAnalyticsOverview] = useState<any>(null);
  const [timeSeries, setTimeSeries] = useState<any[]>([]);
  const [seriesGranularity, setSeriesGranularity] = useState<"Daily" | "Hourly" | "Weekly">("Daily");
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filter Bar State
  const [timeRange, setTimeRange] = useState("Last 30 Days");
  const [selectedOrgScope, setSelectedOrgScope] = useState("ALL");
  const [activeScopeLabel, setActiveScopeLabel] = useState("GLOBAL PLATFORM");

  // Modal State for New Org Creation
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgDomain, setNewOrgDomain] = useState("");
  const [newOrgPlan, setNewOrgPlan] = useState("ENTERPRISE");
  const [newOrgAdminEmail, setNewOrgAdminEmail] = useState("");
  const [newOrgAdminName, setNewOrgAdminName] = useState("");
  const [newOrgAdminPassword, setNewOrgAdminPassword] = useState("");
  const [createMsg, setCreateMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadPlatformData = useCallback(async (orgScope = selectedOrgScope, rangeLabel = timeRange) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const headers: Record<string, string> = {};
      if (orgScope && orgScope !== "ALL") {
        headers["X-Organization-Context"] = scopeToHeader(orgScope);
      }

      const apiRange =
        rangeLabel === "Today" ? "24h" :
        rangeLabel === "Last 7 Days" ? "7d" :
        rangeLabel === "Last 90 Days" ? "90d" : "30d";

      const [ovData, orgsData, anOverview, tsData] = await Promise.all([
        fetchApi("/platform/overview", { headers }),
        fetchApi("/platform/organizations", { headers }),
        fetchApi("/analytics/overview", { headers }).catch(() => null),
        fetchApi(`/analytics/time-series?range=${apiRange}`, { headers }).catch(() => ({ data: [] }))
      ]);
      setOverview(ovData);
      setOrganizations(orgsData || []);
      setAnalyticsOverview(anOverview);
      setTimeSeries(tsData?.data || []);
    } catch (err: any) {
      console.error("Platform dashboard load error:", err);
      setErrorMsg(err.message || "Unable to connect to AGENTGUARD backend API.");
    } finally {
      setLoading(false);
    }
  }, [selectedOrgScope, timeRange]);

  const scopeToHeader = (scopeId: string) => scopeId;

  useEffect(() => {
    loadPlatformData();
  }, [loadPlatformData]);

  const handleOrgScopeChange = (scopeId: string) => {
    setSelectedOrgScope(scopeId);
    if (scopeId === "ALL") {
      setActiveScopeLabel("GLOBAL PLATFORM");
    } else {
      const matched = organizations.find((o) => o.id === scopeId);
      setActiveScopeLabel(matched ? matched.name.toUpperCase() : "TENANT SCOPE");
    }
    loadPlatformData(scopeId, timeRange);
  };

  const handleCreateOrgSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateMsg("");
    setSubmitting(true);
    try {
      const idempotencyKey = `create-org-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const res = await fetchApi("/platform/organizations", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({
          name: newOrgName,
          domain: newOrgDomain,
          plan_id: newOrgPlan,
          admin_email: newOrgAdminEmail,
          admin_full_name: newOrgAdminName,
          admin_password: newOrgAdminPassword || undefined
        })
      });
      if (res.status === "SUCCESS") {
        setCreateMsg(`Organization '${res.name}' provisioned successfully!`);
        setShowCreateModal(false);
        setNewOrgName("");
        setNewOrgDomain("");
        setNewOrgAdminEmail("");
        setNewOrgAdminName("");
        setNewOrgAdminPassword("");
        loadPlatformData();
      } else {
        setCreateMsg(res.detail?.message || res.detail || "Failed to create organization.");
      }
    } catch (err: any) {
      setCreateMsg(err.message || "Failed to create organization.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStatus = async (orgId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
    try {
      await fetchApi(`/platform/organizations/${orgId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus })
      });
      loadPlatformData();
    } catch (err: any) {
      alert("Status change failed: " + err.message);
    }
  };

  const handleExportDashboard = async () => {
    try {
      const token = localStorage.getItem("agentguard_token") || localStorage.getItem("token");
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/+$/, "");
      const res = await fetch(`${baseUrl}/reports/export/pdf?type=executive`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agentguard-platform-overview-${new Date().toISOString().split("T")[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to export platform report.");
    }
  };

  return (
    <div className="space-y-5 text-[#E1E7F0]">
      {/* Banner / Message Notification */}
      {createMsg && (
        <div className="p-3.5 rounded-[10px] bg-[#173B25] border border-[#2E9D50]/50 text-[#2E9D50] text-[13px] font-bold flex items-center justify-between shadow-sm">
          <span>{createMsg}</span>
          <button onClick={() => setCreateMsg("")} className="text-[11px] text-white hover:underline font-bold">Dismiss</button>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-[10px] bg-[#3B1516] border border-[#E53935]/50 space-y-2 text-[#E53935] shadow-sm">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <h3 className="font-bold text-[14px]">Unable to load Platform Control Center metrics</h3>
          </div>
          <p className="text-[12px] text-[#94A3B8]">{errorMsg}</p>
          <button
            onClick={() => loadPlatformData()}
            className="px-3 py-1 bg-[#E53935] text-white text-[11px] font-bold rounded-[6px] hover:bg-[#C62828] transition-colors"
          >
            Retry Request
          </button>
        </div>
      )}

      {/* 1. GLOBAL FILTER BAR */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-4 text-[12px]">
          {/* Time Range Selector */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#94A3B8]">Time Range</span>
            <div className="relative">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="bg-[#161C2A] border border-[#232F48] text-white text-[12px] font-bold rounded-[6px] pl-3 pr-8 py-1.5 outline-none focus:border-[#2E9D50] cursor-pointer appearance-none"
              >
                <option>Today</option>
                <option>Last 7 Days</option>
                <option>Last 30 Days</option>
                <option>Last 90 Days</option>
                <option>Custom Range</option>
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#94A3B8] absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>

          <div className="w-[1px] h-6 bg-[#1E2638] hidden sm:block" />

          {/* Organization Scope Selector */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#94A3B8]">Organization Scope</span>
            <div className="relative">
              <select
                value={selectedOrgScope}
                onChange={(e) => handleOrgScopeChange(e.target.value)}
                className="bg-[#161C2A] border border-[#232F48] text-white text-[12px] font-bold rounded-[6px] pl-3 pr-8 py-1.5 outline-none focus:border-[#2E9D50] cursor-pointer appearance-none"
              >
                <option value="ALL">All Organizations (Global)</option>
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>{org.name}</option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#94A3B8] absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3.5 py-1.5 bg-[#173B25] hover:bg-[#237A3C] text-[#2E9D50] hover:text-white border border-[#2E9D50]/50 text-[12px] font-bold rounded-[6px] transition-colors flex items-center justify-center gap-2 shadow-xs shrink-0"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Organization</span>
          </button>
          <button
            onClick={handleExportDashboard}
            className="px-3.5 py-1.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[12px] font-bold rounded-[6px] transition-colors flex items-center justify-center gap-2 shadow-xs shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      {/* 2. KPI METRICS CARDS */}
      <div className="space-y-3">
        {/* KPI Row 1 (5 Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {/* Card 1: Total Organizations */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL ORGANIZATIONS</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <Building className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">
                {overview?.total_organizations ?? 0}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8] flex items-center gap-1">
              {overview?.active_organizations ?? 0} active organizations
            </span>
          </div>

          {/* Card 2: Active Organizations */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">ACTIVE ORGANIZATIONS</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <CheckCircle className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">
                {overview?.active_organizations ?? 0}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50]">
              {overview?.total_organizations
                ? `${Math.round(((overview.active_organizations ?? 0) / overview.total_organizations) * 100)}% operational`
                : "0% operational"}
            </span>
          </div>

          {/* Card 3: Total Human Users */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL HUMAN USERS</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <Users className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">
                {overview?.total_users ?? 0}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">
              Across provisioned tenants
            </span>
          </div>

          {/* Card 4: Total AI Agents */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL AI AGENTS</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <Bot className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">
                {overview?.total_ai_agents ?? 0}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">
              Registered AI identities
            </span>
          </div>

          {/* Card 5: Active Licenses */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">ACTIVE LICENSES</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">
                {overview?.active_licenses ?? 0}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">
              {overview?.expiring_licenses ?? 0} expiring soon
            </span>
          </div>
        </div>

        {/* KPI Row 2 (5 Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {/* Card 6: Expiring Licenses */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#F59A23]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">EXPIRING LICENSES</span>
              <div className="w-8 h-8 rounded-full bg-[#3D2910] text-[#F59A23] flex items-center justify-center shrink-0 border border-[#F59A23]/30">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#F59A23] leading-none">{overview?.expiring_licenses ?? 0}</h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">Expiring within 30 days</span>
          </div>

          {/* Card 7: Total API Keys */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL API KEYS</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <Key className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">
                {overview?.total_api_keys ?? 0}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">
              Provisioned API keys
            </span>
          </div>

          {/* Card 8: Security Incidents */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#E53935]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">SECURITY INCIDENTS</span>
              <div className="w-8 h-8 rounded-full bg-[#3B1516] text-[#E53935] flex items-center justify-center shrink-0 border border-[#E53935]/30">
                <ShieldAlert className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#E53935] leading-none">
                {overview?.security_incidents ?? 0}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">{overview?.critical_incidents ?? 0} critical severity</span>
          </div>

          {/* Card 9: Audit Events */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">AUDIT EVENTS</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <FileSearch className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">{(overview?.audit_events ?? 0).toLocaleString()}</h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">Immutable ledger entries</span>
          </div>

          {/* Card 10: Platform Decisions */}
          <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">DECISIONS EVALUATED</span>
              <div className="w-8 h-8 rounded-full bg-[#173B25] text-[#2E9D50] flex items-center justify-center shrink-0 border border-[#2E9D50]/30">
                <Activity className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#161C2A] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-white leading-none">{(analyticsOverview?.total_decisions ?? 0).toLocaleString()}</h2>
            )}
            <span className="text-[11px] font-bold text-[#94A3B8]">{analyticsOverview?.allow_rate ?? 0}% allow rate</span>
          </div>
        </div>
      </div>

      {/* 3. MAIN ROW 1: Platform Usage Line Chart + Organizations Donut + License Health */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Platform Usage Line Chart */}
        <div className="lg:col-span-5 bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-4 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[15px]">Platform Usage Telemetry</h3>
            <select
              value={seriesGranularity}
              onChange={(e) => setSeriesGranularity(e.target.value as "Daily" | "Hourly" | "Weekly")}
              className="bg-[#161C2A] border border-[#232F48] text-white text-[11px] font-bold rounded-[6px] px-2 py-1 outline-none"
            >
              <option value="Daily">Daily</option>
              <option value="Hourly">Hourly</option>
              <option value="Weekly">Weekly</option>
            </select>
          </div>

          {/* Dynamic SVG Line Graph from Live Analytics */}
          {(() => {
            const pts = timeSeries.length > 12 ? timeSeries.slice(-12) : timeSeries;
            const maxVal = Math.max(1, ...pts.map((p) => Number(p.decisions || 0)));
            const toPoints = (key: "decisions" | "allowed") =>
              pts.map((p, idx) => {
                const x = pts.length <= 1 ? 250 : Math.round((idx / (pts.length - 1)) * 500);
                const y = Math.round(125 - (Number(p[key] || 0) / maxVal) * 100);
                return `${x},${y}`;
              }).join(" ");
            return pts.length === 0 ? (
              <div className="h-44 flex items-center justify-center text-[12px] text-[#64748B] font-mono">
                No telemetry data recorded for this period.
              </div>
            ) : (
              <div className="h-44 w-full relative pt-2 pb-1">
                <svg className="w-full h-full overflow-visible" viewBox="0 0 500 140" preserveAspectRatio="none">
                  <line x1="0" y1="25" x2="500" y2="25" stroke="#1E2638" strokeDasharray="3 3" />
                  <line x1="0" y1="65" x2="500" y2="65" stroke="#1E2638" strokeDasharray="3 3" />
                  <line x1="0" y1="105" x2="500" y2="105" stroke="#1E2638" strokeDasharray="3 3" />
                  <polyline fill="none" stroke="#2E9D50" strokeWidth="2.5" points={toPoints("decisions")} />
                  <polyline fill="none" stroke="#2E9D50" strokeWidth="2" strokeDasharray="4 4" points={toPoints("allowed")} />
                </svg>

                <div className="flex justify-between text-[10px] text-[#64748B] font-mono pt-1">
                  {pts.filter((_, i) => i === 0 || i === pts.length - 1 || i % Math.max(1, Math.floor(pts.length / 5)) === 0).map((p, idx) => (
                    <span key={idx}>{p.label || p.date || ""}</span>
                  ))}
                </div>
              </div>
            );
          })()}

          <div className="flex items-center gap-6 pt-2 text-[11px] font-bold border-t border-[#1E2638]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-[#2E9D50]" />
              <span className="text-[#94A3B8]">Evaluated Decisions</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-[#2E9D50] border-t border-dashed border-[#2E9D50]" />
              <span className="text-[#94A3B8]">Approved Decisions</span>
            </div>
          </div>
        </div>

        {/* Center: Organizations by Status Donut Chart */}
        {(() => {
          const totalOrgs = overview?.total_organizations ?? 0;
          const activeOrgs = overview?.active_organizations ?? 0;
          const suspendedOrgs = overview?.suspended_organizations ?? 0;
          const otherOrgs = Math.max(0, totalOrgs - activeOrgs - suspendedOrgs);
          const activePct = totalOrgs ? Math.round((activeOrgs / totalOrgs) * 100) : 0;
          const suspPct = totalOrgs ? Math.round((suspendedOrgs / totalOrgs) * 100) : 0;
          const otherPct = totalOrgs ? Math.max(0, 100 - activePct - suspPct) : 0;
          const circumference = 289;
          const dashOffset = totalOrgs ? Math.round(circumference * (1 - activeOrgs / totalOrgs)) : circumference;

          return (
            <div className="lg:col-span-4 bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-3 shadow-sm flex flex-col justify-between">
              <h3 className="font-bold text-white text-[15px]">Organizations by Status</h3>

              <div className="flex items-center gap-4">
                <div className="relative shrink-0">
                  <svg className="w-32 h-32 transform -rotate-90">
                    <circle cx="64" cy="64" r="46" stroke="#1E2638" strokeWidth="14" fill="transparent" />
                    <circle cx="64" cy="64" r="46" stroke="#2E9D50" strokeWidth="14" fill="transparent" strokeDasharray={circumference} strokeDashoffset={dashOffset} />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span className="text-[24px] font-bold text-white leading-none">{totalOrgs}</span>
                    <span className="text-[10px] text-[#64748B] font-mono">Total</span>
                  </div>
                </div>

                <div className="space-y-1.5 text-[11px] flex-1">
                  <div className="flex items-center justify-between font-bold">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50]" />
                      <span className="text-[#94A3B8]">Active</span>
                    </div>
                    <span className="text-white">{activeOrgs} ({activePct}%)</span>
                  </div>
                  <div className="flex items-center justify-between font-bold">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#F59A23]" />
                      <span className="text-[#94A3B8]">Suspended</span>
                    </div>
                    <span className={suspendedOrgs > 0 ? "text-[#F59A23]" : "text-[#64748B]"}>{suspendedOrgs} ({suspPct}%)</span>
                  </div>
                  <div className="flex items-center justify-between font-bold">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#64748B]" />
                      <span className="text-[#94A3B8]">Inactive / Other</span>
                    </div>
                    <span className="text-[#64748B]">{otherOrgs} ({otherPct}%)</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {/* Right: License Health Panel */}
        {(() => {
          const lh = overview?.license_health || {};
          const healthy = lh.healthy ?? 0;
          const expiringSoon = lh.expiring_soon ?? 0;
          const expired = lh.expired ?? 0;
          const suspended = lh.suspended ?? 0;
          const totalLic = Math.max(1, healthy + expiringSoon + expired + suspended);
          const pct = (v: number) => Math.round((v / totalLic) * 100);
          const hasAny = (healthy + expiringSoon + expired + suspended) > 0;

          return (
            <div className="lg:col-span-3 bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-3 shadow-sm flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-white text-[15px]">License Health</h3>
                <Link href="/platform/licenses" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
              </div>

              <div className="space-y-2 text-[11px]">
                <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-[#2E9D50]" />
                    <span className="font-bold text-white">Healthy</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-white block text-[13px] leading-none">{healthy}</span>
                    <span className="text-[9px] text-[#64748B]">{hasAny ? pct(healthy) : 0}% of total</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2 bg-[#3D2910]/40 rounded-[6px] border border-[#F59A23]/30">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-[#F59A23]" />
                    <span className="font-bold text-white">Expiring Soon (≤ 30 days)</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-[#F59A23] block text-[13px] leading-none">{expiringSoon}</span>
                    <span className="text-[9px] text-[#64748B]">{hasAny ? pct(expiringSoon) : 0}% of total</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
                  <div className="flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-[#E53935]" />
                    <span className="font-bold text-white">Expired</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-white block text-[13px] leading-none">{expired}</span>
                    <span className="text-[9px] text-[#64748B]">{hasAny ? pct(expired) : 0}% of total</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 text-[#64748B]" />
                    <span className="font-bold text-white">Suspended</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-white block text-[13px] leading-none">{suspended}</span>
                    <span className="text-[9px] text-[#64748B]">{hasAny ? pct(suspended) : 0}% of total</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}
      </div>

      {/* 4. MAIN ROW 2: Recent Organizations Table + Security Overview + Recent Audit Events */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Recent Organizations Table (5 cols) */}
        <div className="lg:col-span-5 bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[15px]">Recent Organizations</h3>
            <Link href="/platform/organizations" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="overflow-x-auto border border-[#1E2638] rounded-[6px]">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[9px] font-bold text-[#64748B] uppercase font-mono">
                <tr>
                  <th className="py-2 px-2.5">Organization</th>
                  <th className="py-2 px-2.5">Plan</th>
                  <th className="py-2 px-2.5 text-center">Users</th>
                  <th className="py-2 px-2.5 text-center">Agents</th>
                  <th className="py-2 px-2.5">Status</th>
                  <th className="py-2 px-2.5">Expiry</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2638]">
                {organizations.slice(0, 5).map((org) => (
                  <tr key={org.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-2.5 px-2.5 font-bold text-white truncate max-w-[120px]">{org.name}</td>
                    <td className="py-2.5 px-2.5">
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[#161C2A] text-[#94A3B8] border border-[#232F48] font-mono">
                        {org.plan_id}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-center font-bold text-white">{org.user_count}</td>
                    <td className="py-2.5 px-2.5 text-center font-bold text-white">{org.agent_count}</td>
                    <td className="py-2.5 px-2.5">
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                        {org.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 font-mono text-[10px] text-[#64748B]">
                      {org.expiry_date ? new Date(org.expiry_date).toISOString().split("T")[0] : "No expiry"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Center: Security Overview Panel (3 cols) */}
        <div className="lg:col-span-3 bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[15px]">Security Overview</h3>
            <Link href="/platform/security" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-3.5 h-3.5 text-[#E53935]" />
                <span className="font-bold text-white">Critical Risks</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">{overview?.security_overview?.critical_risks ?? overview?.critical_incidents ?? 0}</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-[#F59A23]" />
                <span className="font-bold text-white">Security Incidents</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">{overview?.security_overview?.incidents ?? overview?.security_incidents ?? 0}</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
              <div className="flex items-center gap-2">
                <Lock className="w-3.5 h-3.5 text-[#2E9D50]" />
                <span className="font-bold text-white">Blocked Actions</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">{overview?.security_overview?.blocked_actions ?? 0}</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
              <div className="flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-[#8064C8]" />
                <span className="font-bold text-white">Suspended Users</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">{overview?.security_overview?.suspended_users ?? 0}</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px] border border-[#232F48]">
              <div className="flex items-center gap-2">
                <Bot className="w-3.5 h-3.5 text-[#64748B]" />
                <span className="font-bold text-white">Suspended Agents</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">{overview?.security_overview?.suspended_agents ?? 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Recent Audit Events Table (4 cols) */}
        <div className="lg:col-span-4 bg-[#121722] border border-[#1E2638] rounded-[10px] p-4 space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[15px]">Recent Audit Events</h3>
            <Link href="/platform/audit" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="overflow-x-auto border border-[#1E2638] rounded-[6px]">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[9px] font-bold text-[#64748B] uppercase font-mono">
                <tr>
                  <th className="py-2 px-2">Time</th>
                  <th className="py-2 px-2">Actor</th>
                  <th className="py-2 px-2">Action</th>
                  <th className="py-2 px-2">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2638]">
                {(overview?.recent_audits || []).length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-[#64748B] text-[11px]">
                      No audit records found.
                    </td>
                  </tr>
                ) : (
                  (overview?.recent_audits || []).map((audit: any) => (
                    <tr key={audit.id} className="hover:bg-[#161C2A]">
                      <td className="py-2 px-2 font-mono text-[10px] text-[#64748B]">
                        {audit.time ? new Date(audit.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Just now"}
                      </td>
                      <td className="py-2 px-2 font-bold text-white truncate max-w-[100px]">{audit.actor}</td>
                      <td className="py-2 px-2 text-[#94A3B8] truncate max-w-[120px]">{audit.action}</td>
                      <td className="py-2 px-2">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase font-mono border ${
                          audit.result === "SUCCESS"
                            ? "bg-[#173B25] text-[#2E9D50] border-[#2E9D50]/30"
                            : "bg-[#3B1516] text-[#E53935] border-[#E53935]/30"
                        }`}>
                          {audit.result}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* CREATE ORG MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-6 max-w-md w-full space-y-4 shadow-2xl text-[13px]">
            <div className="flex items-center justify-between border-b border-[#1E2638] pb-3">
              <h3 className="font-bold text-white text-[16px]">Provision New Organization</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-[#64748B] hover:text-white font-bold">✕</button>
            </div>

            <form onSubmit={handleCreateOrgSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] mb-1">Organization Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Technologies"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] mb-1">Domain</label>
                <input
                  type="text"
                  placeholder="e.g. acme.com"
                  value={newOrgDomain}
                  onChange={(e) => setNewOrgDomain(e.target.value)}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] mb-1">Subscription Plan</label>
                <select
                  value={newOrgPlan}
                  onChange={(e) => setNewOrgPlan(e.target.value)}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                >
                  <option value="STARTER">STARTER</option>
                  <option value="PROFESSIONAL">PROFESSIONAL</option>
                  <option value="ENTERPRISE">ENTERPRISE</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] mb-1">Admin Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. John Doe"
                  value={newOrgAdminName}
                  onChange={(e) => setNewOrgAdminName(e.target.value)}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] mb-1">Admin Email</label>
                <input
                  type="email"
                  required
                  placeholder="admin@acme.com"
                  value={newOrgAdminEmail}
                  onChange={(e) => setNewOrgAdminEmail(e.target.value)}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] mb-1">Initial Password (Optional)</label>
                <input
                  type="password"
                  placeholder="Leave blank to auto-generate a secure random password"
                  value={newOrgAdminPassword}
                  onChange={(e) => setNewOrgAdminPassword(e.target.value)}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1E2638]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-[#161C2A] text-[#94A3B8] hover:text-white rounded-[8px] font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] font-bold disabled:opacity-50"
                >
                  {submitting ? "Provisioning..." : "Provision Organization"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
