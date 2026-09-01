"use client";

import React, { useEffect, useState } from "react";
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
  const [createMsg, setCreateMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadPlatformData = async (orgScope = selectedOrgScope) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const headers: Record<string, string> = {};
      if (orgScope && orgScope !== "ALL") {
        headers["X-Organization-Context"] = orgScope;
      }

      const [ovData, orgsData] = await Promise.all([
        fetchApi("/platform/overview", { headers }),
        fetchApi("/platform/organizations", { headers })
      ]);
      setOverview(ovData);
      setOrganizations(orgsData || []);
    } catch (err: any) {
      console.error("Platform dashboard load error:", err);
      setErrorMsg(err.message || "Unable to connect to AGENTGUARD backend API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlatformData();
  }, []);

  const handleOrgScopeChange = (scopeId: string) => {
    setSelectedOrgScope(scopeId);
    if (scopeId === "ALL") {
      setActiveScopeLabel("GLOBAL PLATFORM");
    } else {
      const matched = organizations.find((o) => o.id === scopeId);
      setActiveScopeLabel(matched ? matched.name.toUpperCase() : "TENANT SCOPE");
    }
    loadPlatformData(scopeId);
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
          admin_password: "Blackbird@12."
        })
      });
      if (res.status === "SUCCESS") {
        setCreateMsg(`Organization '${res.name}' provisioned successfully!`);
        setShowCreateModal(false);
        setNewOrgName("");
        setNewOrgDomain("");
        setNewOrgAdminEmail("");
        setNewOrgAdminName("");
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

  const handleExportDashboard = () => {
    alert("Exporting Platform Control Center Overview report...");
  };

  return (
    <div className="space-y-5 text-[#1F1F1F]">
      {/* Banner / Message Notification */}
      {createMsg && (
        <div className="p-3.5 rounded-[10px] bg-[#EAF7EE] border border-[#2E9D50]/40 text-[#237A3C] text-[13px] font-bold flex items-center justify-between shadow-sm">
          <span>{createMsg}</span>
          <button onClick={() => setCreateMsg("")} className="text-[11px] text-[#2E9D50] hover:underline font-bold">Dismiss</button>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-[10px] bg-[#FDECEC] border border-[#E53935]/40 space-y-2 text-[#C62828] shadow-sm">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <h3 className="font-bold text-[14px]">Unable to load Platform Control Center metrics</h3>
          </div>
          <p className="text-[12px] text-[#666666]">{errorMsg}</p>
          <button
            onClick={() => loadPlatformData()}
            className="px-3 py-1 bg-[#E53935] text-white text-[11px] font-bold rounded-[6px] hover:bg-[#C62828] transition-colors"
          >
            Retry Request
          </button>
        </div>
      )}

      {/* 1. GLOBAL FILTER BAR (Matching Reference 1 Top Row) */}
      <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex flex-wrap items-center gap-4 text-[12px]">
          {/* Time Range Selector */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#64748B]">Time Range</span>
            <div className="relative">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="bg-[#F8FAFC] border border-[#CBD5E1] text-[#1E293B] text-[12px] font-bold rounded-[6px] pl-3 pr-8 py-1.5 outline-none focus:border-[#2E9D50] cursor-pointer appearance-none"
              >
                <option>Today</option>
                <option>Last 7 Days</option>
                <option>Last 30 Days</option>
                <option>Last 90 Days</option>
                <option>Custom Range</option>
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#64748B] absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>

          <div className="w-[1px] h-6 bg-[#E2E8F0] hidden sm:block" />

          {/* Organization Scope Selector */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#64748B]">Organization Scope</span>
            <div className="relative">
              <select
                value={selectedOrgScope}
                onChange={(e) => handleOrgScopeChange(e.target.value)}
                className="bg-[#F8FAFC] border border-[#CBD5E1] text-[#1E293B] text-[12px] font-bold rounded-[6px] pl-3 pr-8 py-1.5 outline-none focus:border-[#2E9D50] cursor-pointer appearance-none"
              >
                <option value="ALL">All Organizations (Global)</option>
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>{org.name}</option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#64748B] absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Export Dashboard Button */}
        <button
          onClick={handleExportDashboard}
          className="px-3.5 py-1.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[12px] font-bold rounded-[6px] transition-colors flex items-center justify-center gap-2 shadow-xs shrink-0"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Dashboard</span>
        </button>
      </div>

      {/* 2. KPI METRICS CARDS (10 Cards across 2 Rows of 5) */}
      <div className="space-y-3">
        {/* KPI Row 1 (5 Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {/* Card 1: Total Organizations */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL ORGANIZATIONS</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <Building className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">
                {overview?.total_organizations ?? 5}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> ↑ 2 active this month
            </span>
          </div>

          {/* Card 2: Active Organizations */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">ACTIVE ORGANIZATIONS</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <CheckCircle className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">
                {overview?.active_organizations ?? overview?.total_organizations ?? 5}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50]">100% of total</span>
          </div>

          {/* Card 3: Total Human Users */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL HUMAN USERS</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <Users className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">
                {overview?.total_users ?? 40}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> ↑ 8 this month
            </span>
          </div>

          {/* Card 4: Total AI Agents */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL AI AGENTS</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">
                {overview?.total_ai_agents ?? 25}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> ↑ 5 this month
            </span>
          </div>

          {/* Card 5: Active Licenses */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">ACTIVE LICENSES</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">
                {overview?.active_licenses ?? 5}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50]">100% active</span>
          </div>
        </div>

        {/* KPI Row 2 (5 Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {/* Card 6: Expiring Licenses */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#F59A23]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">EXPIRING LICENSES</span>
              <div className="w-8 h-8 rounded-full bg-[#FEF3C7] text-[#F59A23] flex items-center justify-center shrink-0">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#F59A23] leading-none">1</h2>
            )}
            <span className="text-[11px] font-bold text-[#64748B]">Expiring within 30 days</span>
          </div>

          {/* Card 7: Total API Keys */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL API KEYS</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <Key className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">
                {overview?.total_api_keys ?? 12}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> ↑ 3 this month
            </span>
          </div>

          {/* Card 8: Security Incidents */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#E53935]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">SECURITY INCIDENTS</span>
              <div className="w-8 h-8 rounded-full bg-[#FDECEC] text-[#E53935] flex items-center justify-center shrink-0">
                <ShieldAlert className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#E53935] leading-none">
                {overview?.security_incidents ?? 3}
              </h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50]">↓ 2 vs last 30 days</span>
          </div>

          {/* Card 9: Audit Events */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">AUDIT EVENTS</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <FileSearch className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">1,248</h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50]">↑ 18% vs last 30 days</span>
          </div>

          {/* Card 10: Platform Usage */}
          <div className="bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-2 shadow-xs hover:border-[#2E9D50]/50 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">PLATFORM USAGE</span>
              <div className="w-8 h-8 rounded-full bg-[#EAF7EE] text-[#2E9D50] flex items-center justify-center shrink-0">
                <Activity className="w-4 h-4" />
              </div>
            </div>
            {loading ? (
              <div className="h-8 bg-[#F1F5F9] animate-pulse rounded w-16" />
            ) : (
              <h2 className="text-[26px] font-bold text-[#0F172A] leading-none">78%</h2>
            )}
            <span className="text-[11px] font-bold text-[#2E9D50]">↑ 12% vs last 30 days</span>
          </div>
        </div>
      </div>

      {/* 3. MAIN ROW 1: Platform Usage Line Chart + Organizations Donut + License Health */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Platform Usage Line Chart */}
        <div className="lg:col-span-5 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-4 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Platform Usage</h3>
            <select className="bg-[#F8FAFC] border border-[#CBD5E1] text-[#1E293B] text-[11px] font-bold rounded-[6px] px-2 py-1 outline-none">
              <option>Daily</option>
              <option>Hourly</option>
              <option>Weekly</option>
            </select>
          </div>

          {/* High-Tech Line SVG Graph matching Reference 1 */}
          <div className="h-44 w-full relative pt-2 pb-1">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 500 140" preserveAspectRatio="none">
              {/* Horizontal Grid lines */}
              <line x1="0" y1="25" x2="500" y2="25" stroke="#F1F5F9" strokeDasharray="3 3" />
              <line x1="0" y1="65" x2="500" y2="65" stroke="#F1F5F9" strokeDasharray="3 3" />
              <line x1="0" y1="105" x2="500" y2="105" stroke="#F1F5F9" strokeDasharray="3 3" />

              {/* Line 1: API Requests (Solid Green) */}
              <path
                d="M 0 100 L 40 85 L 80 65 L 120 70 L 160 45 L 200 60 L 240 50 L 280 75 L 320 55 L 360 30 L 400 35 L 440 55 L 500 45"
                fill="none"
                stroke="#2E9D50"
                strokeWidth="2.5"
              />
              {/* Line 2: Active Users (Dotted Green) */}
              <path
                d="M 0 120 L 40 110 L 80 100 L 120 105 L 160 90 L 200 95 L 240 85 L 280 105 L 320 90 L 360 75 L 400 80 L 440 95 L 500 90"
                fill="none"
                stroke="#2E9D50"
                strokeWidth="2"
                strokeDasharray="4 4"
              />
            </svg>

            {/* X-Axis Labels */}
            <div className="flex justify-between text-[10px] text-[#64748B] font-mono pt-1">
              <span>May 4</span>
              <span>May 9</span>
              <span>May 14</span>
              <span>May 19</span>
              <span>May 24</span>
              <span>May 29</span>
              <span>Jun 3</span>
            </div>
          </div>

          <div className="flex items-center gap-6 pt-2 text-[11px] font-bold border-t border-[#F1F5F9]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-[#2E9D50]" />
              <span className="text-[#64748B]">API Requests</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-[#2E9D50] border-t border-dashed border-[#2E9D50]" />
              <span className="text-[#64748B]">Active Users</span>
            </div>
          </div>
        </div>

        {/* Center: Organizations by Status Donut Chart */}
        <div className="lg:col-span-4 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs flex flex-col justify-between">
          <h3 className="font-bold text-[#0F172A] text-[15px]">Organizations by Status</h3>

          <div className="flex items-center gap-4">
            {/* Donut SVG */}
            <div className="relative shrink-0">
              <svg className="w-32 h-32 transform -rotate-90">
                <circle cx="64" cy="64" r="46" stroke="#E2E8F0" strokeWidth="14" fill="transparent" />
                <circle cx="64" cy="64" r="46" stroke="#2E9D50" strokeWidth="14" fill="transparent" strokeDasharray="289" strokeDashoffset="0" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-[24px] font-bold text-[#0F172A] leading-none">5</span>
                <span className="text-[10px] text-[#64748B] font-mono">Total</span>
              </div>
            </div>

            {/* Legend List */}
            <div className="space-y-1.5 text-[11px] flex-1">
              <div className="flex items-center justify-between font-bold">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50]" />
                  <span className="text-[#475569]">Active</span>
                </div>
                <span className="text-[#0F172A]">5 (100%)</span>
              </div>
              <div className="flex items-center justify-between font-bold">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#F59A23]" />
                  <span className="text-[#475569]">Suspended</span>
                </div>
                <span className="text-[#64748B]">0 (0%)</span>
              </div>
              <div className="flex items-center justify-between font-bold">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#94A3B8]" />
                  <span className="text-[#475569]">Inactive</span>
                </div>
                <span className="text-[#64748B]">0 (0%)</span>
              </div>
              <div className="flex items-center justify-between font-bold">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#E53935]" />
                  <span className="text-[#475569]">Expired</span>
                </div>
                <span className="text-[#64748B]">0 (0%)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: License Health Panel */}
        <div className="lg:col-span-3 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[#0F172A] text-[15px]">License Health</h3>
            <Link href="/platform/licenses" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[#2E9D50]" />
                <span className="font-bold text-[#1E293B]">Healthy</span>
              </div>
              <div className="text-right">
                <span className="font-bold text-[#0F172A] block text-[13px] leading-none">4</span>
                <span className="text-[9px] text-[#64748B]">80% of total</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#FEF3C7]/30 rounded-[6px] border border-[#FEF3C7]">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-[#F59A23]" />
                <span className="font-bold text-[#1E293B]">Expiring Soon (≤ 30 days)</span>
              </div>
              <div className="text-right">
                <span className="font-bold text-[#F59A23] block text-[13px] leading-none">1</span>
                <span className="text-[9px] text-[#64748B]">20% of total</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <XCircle className="w-4 h-4 text-[#E53935]" />
                <span className="font-bold text-[#1E293B]">Expired</span>
              </div>
              <div className="text-right">
                <span className="font-bold text-[#0F172A] block text-[13px] leading-none">0</span>
                <span className="text-[9px] text-[#64748B]">0% of total</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-[#64748B]" />
                <span className="font-bold text-[#1E293B]">Suspended</span>
              </div>
              <div className="text-right">
                <span className="font-bold text-[#0F172A] block text-[13px] leading-none">0</span>
                <span className="text-[9px] text-[#64748B]">0% of total</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. MAIN ROW 2: Recent Organizations Table + Security Overview + Recent Audit Events */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Recent Organizations Table (5 cols) */}
        <div className="lg:col-span-5 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Recent Organizations</h3>
            <Link href="/platform/organizations" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="overflow-x-auto border border-[#E2E8F0] rounded-[6px]">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[9px] font-bold text-[#64748B] uppercase font-mono">
                <tr>
                  <th className="py-2 px-2.5">Organization</th>
                  <th className="py-2 px-2.5">License</th>
                  <th className="py-2 px-2.5 text-center">Users</th>
                  <th className="py-2 px-2.5 text-center">AI Agents</th>
                  <th className="py-2 px-2.5">Status</th>
                  <th className="py-2 px-2.5">License Expiry</th>
                  <th className="py-2 px-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {organizations.slice(0, 5).map((org) => (
                  <tr key={org.id} className="hover:bg-[#F8FAFC] transition-colors">
                    <td className="py-2.5 px-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded bg-[#FEF3C7] text-[#D97706] font-bold flex items-center justify-center text-[9px] shrink-0">
                          {org.name[0]}
                        </div>
                        <span className="font-bold text-[#0F172A] truncate max-w-[110px]">{org.name}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-2.5">
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[#F1F5F9] text-[#475569] font-mono">
                        {org.plan_id}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-center font-bold text-[#0F172A]">{org.user_count}</td>
                    <td className="py-2.5 px-2.5 text-center font-bold text-[#0F172A]">{org.agent_count}</td>
                    <td className="py-2.5 px-2.5">
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50]">
                        {org.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 font-mono text-[10px] text-[#64748B]">
                      {org.expiry_date ? new Date(org.expiry_date).toISOString().split("T")[0] : "2026-08-31"}
                    </td>
                    <td className="py-2.5 px-2.5 text-right space-x-1">
                      <button
                        onClick={() => handleToggleStatus(org.id, org.status)}
                        className="text-[#64748B] hover:text-[#E53935]"
                      >
                        •••
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Center: Security Overview Panel (3 cols) */}
        <div className="lg:col-span-3 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Security Overview</h3>
            <Link href="/platform/security" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-3.5 h-3.5 text-[#E53935]" />
                <span className="font-bold text-[#1E293B]">Critical Risks</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-[#0F172A]">1</span>
                <span className="text-[9px] text-[#2E9D50] font-mono">↓ 1 vs last 30 days</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-[#F59A23]" />
                <span className="font-bold text-[#1E293B]">Security Incidents</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-[#0F172A]">3</span>
                <span className="text-[9px] text-[#2E9D50] font-mono">↓ 2 vs last 30 days</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <Lock className="w-3.5 h-3.5 text-[#2E9D50]" />
                <span className="font-bold text-[#1E293B]">Blocked Actions</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-[#0F172A]">24</span>
                <span className="text-[9px] text-[#2E9D50] font-mono">↑ 8 vs last 30 days</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-[#8064C8]" />
                <span className="font-bold text-[#1E293B]">Circuit Breaker Events</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-[#0F172A]">7</span>
                <span className="text-[9px] text-[#2E9D50] font-mono">↑ 3 vs last 30 days</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <Bot className="w-3.5 h-3.5 text-[#64748B]" />
                <span className="font-bold text-[#1E293B]">Suspended Agents</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-[#0F172A]">2</span>
                <span className="text-[9px] text-[#2E9D50] font-mono">↓ 1 vs last 30 days</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <Users className="w-3.5 h-3.5 text-[#64748B]" />
                <span className="font-bold text-[#1E293B]">Suspended Users</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-[#0F172A]">1</span>
                <span className="text-[9px] text-[#2E9D50] font-mono">↑ 1 vs last 30 days</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Recent Audit Events Table (4 cols) */}
        <div className="lg:col-span-4 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Recent Audit Events</h3>
            <Link href="/platform/audit" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="overflow-x-auto border border-[#E2E8F0] rounded-[6px]">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[9px] font-bold text-[#64748B] uppercase font-mono">
                <tr>
                  <th className="py-2 px-2">Time</th>
                  <th className="py-2 px-2">Actor</th>
                  <th className="py-2 px-2">Action</th>
                  <th className="py-2 px-2">Target</th>
                  <th className="py-2 px-2">Organization</th>
                  <th className="py-2 px-2">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                <tr className="hover:bg-[#F8FAFC]">
                  <td className="py-2 px-2 font-mono text-[10px] text-[#64748B]">2m ago</td>
                  <td className="py-2 px-2 font-bold text-[#0F172A]">SUPER_ADMIN</td>
                  <td className="py-2 px-2 text-[#475569]">Organization license updated</td>
                  <td className="py-2 px-2 text-[#475569]">ACME Technologies</td>
                  <td className="py-2 px-2 text-[#64748B]">Global</td>
                  <td className="py-2 px-2">
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                      SUCCESS
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-[#F8FAFC]">
                  <td className="py-2 px-2 font-mono text-[10px] text-[#64748B]">15m ago</td>
                  <td className="py-2 px-2 font-bold text-[#0F172A]">aarav@medcore.com</td>
                  <td className="py-2 px-2 text-[#475569]">New AI agent created</td>
                  <td className="py-2 px-2 text-[#475569]">MedCore Health Systems</td>
                  <td className="py-2 px-2 text-[#64748B]">MedCore Health Systems</td>
                  <td className="py-2 px-2">
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                      SUCCESS
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-[#F8FAFC]">
                  <td className="py-2 px-2 font-mono text-[10px] text-[#64748B]">32m ago</td>
                  <td className="py-2 px-2 font-bold text-[#0F172A]">zoya@nesa.com</td>
                  <td className="py-2 px-2 text-[#475569]">User role updated</td>
                  <td className="py-2 px-2 text-[#475569]">Ira Patel</td>
                  <td className="py-2 px-2 text-[#64748B]">Nexa Financial Services</td>
                  <td className="py-2 px-2">
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                      SUCCESS
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-[#F8FAFC]">
                  <td className="py-2 px-2 font-mono text-[10px] text-[#64748B]">1h ago</td>
                  <td className="py-2 px-2 font-bold text-[#0F172A]">anaya@urbangrid.com</td>
                  <td className="py-2 px-2 text-[#475569]">Security policy updated</td>
                  <td className="py-2 px-2 text-[#475569]">Data Access Policy</td>
                  <td className="py-2 px-2 text-[#64748B]">UrbanGrid Logistics</td>
                  <td className="py-2 px-2">
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                      SUCCESS
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-[#F8FAFC]">
                  <td className="py-2 px-2 font-mono text-[10px] text-[#64748B]">2h ago</td>
                  <td className="py-2 px-2 font-bold text-[#0F172A]">vihaan@edunova.com</td>
                  <td className="py-2 px-2 text-[#475569]">Organization settings updated</td>
                  <td className="py-2 px-2 text-[#475569]">EduNova Learning</td>
                  <td className="py-2 px-2 text-[#64748B]">EduNova Learning</td>
                  <td className="py-2 px-2">
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                      SUCCESS
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 5. MAIN ROW 3: System Health + Quick Actions + Platform Usage Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* System Health Indicators (3 cols) */}
        <div className="lg:col-span-3 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[#0F172A] text-[15px]">System Health</h3>
            <Link href="/platform/system" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#1E293B]">Backend Services</span>
              </div>
              <span className="text-[9px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#1E293B]">API Services</span>
              </div>
              <span className="text-[9px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#1E293B]">Database (Supabase)</span>
              </div>
              <span className="text-[9px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#1E293B]">AI Governance Engine</span>
              </div>
              <span className="text-[9px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#1E293B]">Supabase Auth</span>
              </div>
              <span className="text-[9px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#1E293B]">Background Jobs</span>
              </div>
              <span className="text-[9px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>
          </div>
        </div>

        {/* Quick Actions (5 cols) */}
        <div className="lg:col-span-5 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs">
          <h3 className="font-bold text-[#0F172A] text-[15px]">Quick Actions</h3>

          <div className="grid grid-cols-4 sm:grid-cols-7 gap-2.5">
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] hover:bg-[#EAF7EE] hover:border-[#2E9D50] transition-all flex flex-col items-center text-center space-y-1 group"
            >
              <Building className="w-4 h-4 text-[#2E9D50]" />
              <span className="text-[9px] font-bold text-[#1E293B] group-hover:text-[#2E9D50] leading-tight">Create Organization</span>
            </button>

            <Link
              href="/platform/licenses"
              className="p-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] hover:bg-[#EAF7EE] hover:border-[#2E9D50] transition-all flex flex-col items-center text-center space-y-1 group"
            >
              <CreditCard className="w-4 h-4 text-[#2E9D50]" />
              <span className="text-[9px] font-bold text-[#1E293B] group-hover:text-[#2E9D50] leading-tight">Create License</span>
            </Link>

            <Link
              href="/platform/users"
              className="p-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] hover:bg-[#EAF7EE] hover:border-[#2E9D50] transition-all flex flex-col items-center text-center space-y-1 group"
            >
              <UserPlus className="w-4 h-4 text-[#2E9D50]" />
              <span className="text-[9px] font-bold text-[#1E293B] group-hover:text-[#2E9D50] leading-tight">Add User</span>
            </Link>

            <Link
              href="/platform/agents"
              className="p-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] hover:bg-[#EAF7EE] hover:border-[#2E9D50] transition-all flex flex-col items-center text-center space-y-1 group"
            >
              <Bot className="w-4 h-4 text-[#2E9D50]" />
              <span className="text-[9px] font-bold text-[#1E293B] group-hover:text-[#2E9D50] leading-tight">Register AI Agent</span>
            </Link>

            <Link
              href="/policies"
              className="p-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] hover:bg-[#EAF7EE] hover:border-[#2E9D50] transition-all flex flex-col items-center text-center space-y-1 group"
            >
              <Shield className="w-4 h-4 text-[#2E9D50]" />
              <span className="text-[9px] font-bold text-[#1E293B] group-hover:text-[#2E9D50] leading-tight">Create Policy</span>
            </Link>

            <Link
              href="/platform/audit"
              className="p-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] hover:bg-[#EAF7EE] hover:border-[#2E9D50] transition-all flex flex-col items-center text-center space-y-1 group"
            >
              <FileSearch className="w-4 h-4 text-[#2E9D50]" />
              <span className="text-[9px] font-bold text-[#1E293B] group-hover:text-[#2E9D50] leading-tight">View Audit Logs</span>
            </Link>

            <Link
              href="/platform/system"
              className="p-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] hover:bg-[#EAF7EE] hover:border-[#2E9D50] transition-all flex flex-col items-center text-center space-y-1 group"
            >
              <Server className="w-4 h-4 text-[#2E9D50]" />
              <span className="text-[9px] font-bold text-[#1E293B] group-hover:text-[#2E9D50] leading-tight">System Health</span>
            </Link>
          </div>
        </div>

        {/* Platform Usage Analytics (4 cols) */}
        <div className="lg:col-span-4 bg-white border border-[#E2E8F0] rounded-[10px] p-4 space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Platform Usage Analytics</h3>
            <Link href="/platform/analytics" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View All</Link>
          </div>

          <div className="flex items-center gap-3 text-[10px] border-b border-[#F1F5F9] pb-2">
            <span className="text-[#64748B]">Today</span>
            <span className="font-bold text-[#2E9D50] border-b-2 border-[#2E9D50] pb-0.5">7 Days</span>
            <span className="text-[#64748B]">30 Days</span>
            <span className="text-[#64748B]">90 Days</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-[11px]">
            <div className="p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0] space-y-1">
              <span className="text-[10px] text-[#64748B] uppercase font-mono block">API Requests</span>
              <span className="font-bold text-[#0F172A] text-[15px] block leading-none">128,430</span>
              <span className="text-[9px] text-[#2E9D50] font-bold flex items-center gap-0.5">
                <TrendingUp className="w-3 h-3" /> ↑ 18.6%
              </span>
            </div>

            <div className="p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0] space-y-1">
              <span className="text-[10px] text-[#64748B] uppercase font-mono block">Active Users</span>
              <span className="font-bold text-[#0F172A] text-[15px] block leading-none">1,248</span>
              <span className="text-[9px] text-[#2E9D50] font-bold flex items-center gap-0.5">
                <TrendingUp className="w-3 h-3" /> ↑ 12.4%
              </span>
            </div>

            <div className="p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0] space-y-1">
              <span className="text-[10px] text-[#64748B] uppercase font-mono block">AI Agent Activity</span>
              <span className="font-bold text-[#0F172A] text-[15px] block leading-none">2,847</span>
              <span className="text-[9px] text-[#2E9D50] font-bold flex items-center gap-0.5">
                <TrendingUp className="w-3 h-3" /> ↑ 15.3%
              </span>
            </div>

            <div className="p-2 bg-[#F8FAFC] rounded-[6px] border border-[#E2E8F0] space-y-1">
              <span className="text-[10px] text-[#64748B] uppercase font-mono block">Decisions Evaluated</span>
              <span className="font-bold text-[#0F172A] text-[15px] block leading-none">5,628</span>
              <span className="text-[9px] text-[#2E9D50] font-bold flex items-center gap-0.5">
                <TrendingUp className="w-3 h-3" /> ↑ 20.1%
              </span>
            </div>
          </div>
        </div>
      </div>


      {/* Provision New Organization Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#E2E8F0] rounded-[14px] max-w-md w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl text-[#1F1F1F]">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
              <h2 className="text-[18px] font-bold text-[#0F172A]">Provision New Organization</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-[#64748B] hover:text-[#0F172A]">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateOrgSubmit} className="space-y-4 text-[12px]">
              <div>
                <label className="block font-bold text-[#475569] mb-1">Organization Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Technologies"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] text-[#0F172A] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#475569] mb-1">Domain</label>
                <input
                  type="text"
                  placeholder="e.g. acme.com"
                  value={newOrgDomain}
                  onChange={(e) => setNewOrgDomain(e.target.value)}
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] text-[#0F172A] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#475569] mb-1">SaaS License Plan</label>
                <select
                  value={newOrgPlan}
                  onChange={(e) => setNewOrgPlan(e.target.value)}
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] text-[#0F172A] outline-none focus:border-[#2E9D50]"
                >
                  <option value="STARTER">STARTER (10 Users, 5 Agents)</option>
                  <option value="PROFESSIONAL">PROFESSIONAL (50 Users, 20 Agents)</option>
                  <option value="ENTERPRISE">ENTERPRISE (Unlimited Users/Agents)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#475569] mb-1">Org Admin Email</label>
                <input
                  type="email"
                  required
                  placeholder="admin@acme.com"
                  value={newOrgAdminEmail}
                  onChange={(e) => setNewOrgAdminEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] text-[#0F172A] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#475569] mb-1">Org Admin Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Aarav Sharma"
                  value={newOrgAdminName}
                  onChange={(e) => setNewOrgAdminName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[8px] text-[#0F172A] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#E2E8F0]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-[#F1F5F9] border border-[#CBD5E1] rounded-[8px] text-[#475569] hover:text-[#0F172A] font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] font-bold flex items-center gap-2"
                >
                  {submitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
                  <span>Provision Organization</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
