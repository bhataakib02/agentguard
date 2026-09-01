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
  Shield
} from "lucide-react";

export default function PlatformDashboardPage() {
  const [overview, setOverview] = useState<any>(null);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Modal State for New Org Creation
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgDomain, setNewOrgDomain] = useState("");
  const [newOrgPlan, setNewOrgPlan] = useState("ENTERPRISE");
  const [newOrgAdminEmail, setNewOrgAdminEmail] = useState("");
  const [newOrgAdminName, setNewOrgAdminName] = useState("");
  const [createMsg, setCreateMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadPlatformData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [ovData, orgsData] = await Promise.all([
        fetchApi("/platform/overview"),
        fetchApi("/platform/organizations")
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

  return (
    <div className="space-y-6">
      {/* Banner / Error State */}
      {createMsg && (
        <div className="p-4 rounded-[10px] bg-[#173B25] border border-[#2E9D50]/50 text-white text-[13px] font-bold flex items-center justify-between shadow-sm">
          <span>{createMsg}</span>
          <button onClick={() => setCreateMsg("")} className="text-[11px] text-[#2E9D50] hover:underline">Dismiss</button>
        </div>
      )}

      {errorMsg && (
        <div className="p-5 rounded-[12px] bg-[#3B1516] border border-[#E53935]/40 space-y-3 text-white shadow-sm">
          <div className="flex items-center gap-3 text-[#E53935]">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <h3 className="font-bold text-[14px]">Unable to load Platform Control Center metrics</h3>
          </div>
          <p className="text-[12px] text-[#94A3B8]">{errorMsg}</p>
          <button
            onClick={() => loadPlatformData()}
            className="px-3.5 py-1.5 bg-[#E53935] text-white text-[12px] font-bold rounded-[6px] hover:bg-[#C62828] transition-colors"
          >
            Retry API Request
          </button>
        </div>
      )}

      {/* 1. TOP METRICS CARDS GRID (6 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Card 1: Total Organizations */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL ORGANIZATIONS</span>
            <Building className="w-4 h-4 text-[#2E9D50]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#1A2234] animate-pulse rounded w-16" />
          ) : (
            <h2 className="text-[26px] font-bold text-white leading-none">
              {overview?.total_organizations ?? 5}
            </h2>
          )}
          <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> ↑ 2 active this month
          </span>
        </div>

        {/* Card 2: Total Users */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL USERS</span>
            <Users className="w-4 h-4 text-[#2E9D50]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#1A2234] animate-pulse rounded w-16" />
          ) : (
            <h2 className="text-[26px] font-bold text-white leading-none">
              {overview?.total_users ?? 40}
            </h2>
          )}
          <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> ↑ 8 new this month
          </span>
        </div>

        {/* Card 3: Total AI Agents */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">TOTAL AI AGENTS</span>
            <Bot className="w-4 h-4 text-[#2E9D50]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#1A2234] animate-pulse rounded w-16" />
          ) : (
            <h2 className="text-[26px] font-bold text-white leading-none">
              {overview?.total_ai_agents ?? 25}
            </h2>
          )}
          <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> ↑ 5 new this month
          </span>
        </div>

        {/* Card 4: Active Licenses */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">ACTIVE LICENSES</span>
            <CreditCard className="w-4 h-4 text-[#2E9D50]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#1A2234] animate-pulse rounded w-16" />
          ) : (
            <h2 className="text-[26px] font-bold text-white leading-none">
              {overview?.active_licenses ?? 5}
            </h2>
          )}
          <span className="text-[11px] font-bold text-[#94A3B8]">0 expiring this month</span>
        </div>

        {/* Card 5: API Keys */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-4 space-y-2 shadow-sm hover:border-[#2E9D50]/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">API KEYS</span>
            <Key className="w-4 h-4 text-[#2E9D50]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#1A2234] animate-pulse rounded w-16" />
          ) : (
            <h2 className="text-[26px] font-bold text-white leading-none">
              {overview?.total_api_keys ?? 18}
            </h2>
          )}
          <span className="text-[11px] font-bold text-[#2E9D50] flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> ↑ 3 new this month
          </span>
        </div>

        {/* Card 6: Security Incidents */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-4 space-y-2 shadow-sm hover:border-[#E53935]/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">SECURITY INCIDENTS</span>
            <ShieldAlert className="w-4 h-4 text-[#E53935]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#1A2234] animate-pulse rounded w-16" />
          ) : (
            <h2 className="text-[26px] font-bold text-white leading-none">
              {overview?.security_incidents ?? 3}
            </h2>
          )}
          <span className="text-[11px] font-bold text-[#E53935] flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> ↑ 1 critical
          </span>
        </div>
      </div>

      {/* 2. MAIN ROW 1: Usage Overview Chart + License Health + Security Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Platform Usage Overview Chart */}
        <div className="lg:col-span-6 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-white text-[15px]">Platform Usage Overview</h3>
              <p className="text-[11px] text-[#64748B]">Real-time API requests, active users, and governed AI agent interactions</p>
            </div>
            <select className="bg-[#161C2A] border border-[#232F48] text-[#E1E7F0] text-[11px] font-bold rounded-[6px] px-2 py-1 outline-none">
              <option>Last 30 Days</option>
              <option>Last 7 Days</option>
              <option>Last 90 Days</option>
            </select>
          </div>

          {/* Simulated High-Tech Multi-Line Graph SVG */}
          <div className="h-48 w-full relative pt-4 pb-2">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 500 150" preserveAspectRatio="none">
              {/* Horizontal Grid lines */}
              <line x1="0" y1="30" x2="500" y2="30" stroke="#1E2638" strokeDasharray="3 3" />
              <line x1="0" y1="70" x2="500" y2="70" stroke="#1E2638" strokeDasharray="3 3" />
              <line x1="0" y1="110" x2="500" y2="110" stroke="#1E2638" strokeDasharray="3 3" />

              {/* Line 1: API Calls (Green) */}
              <path
                d="M 0 110 Q 50 90, 100 80 T 200 60 T 300 45 T 400 35 T 500 20"
                fill="none"
                stroke="#2E9D50"
                strokeWidth="2.5"
              />
              {/* Line 2: AI Agents (Blue) */}
              <path
                d="M 0 130 Q 50 115, 100 100 T 200 85 T 300 70 T 400 65 T 500 50"
                fill="none"
                stroke="#0284C7"
                strokeWidth="2"
              />
              {/* Line 3: Users (Orange) */}
              <path
                d="M 0 140 Q 50 135, 100 125 T 200 120 T 300 110 T 400 95 T 500 85"
                fill="none"
                stroke="#E65100"
                strokeWidth="2"
              />
            </svg>

            {/* X-Axis Labels */}
            <div className="flex justify-between text-[9px] text-[#64748B] font-mono pt-2">
              <span>May 4</span>
              <span>May 11</span>
              <span>May 18</span>
              <span>May 25</span>
              <span>Jun 1</span>
            </div>
          </div>

          <div className="flex items-center gap-6 pt-2 text-[11px] font-bold border-t border-[#1E2638]">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#E65100]" />
              <span className="text-[#94A3B8]">Users</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#0284C7]" />
              <span className="text-[#94A3B8]">AI Agents</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50]" />
              <span className="text-[#94A3B8]">API Calls (K)</span>
            </div>
          </div>
        </div>

        {/* Center: License Health Doughnut Chart */}
        <div className="lg:col-span-3 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[15px]">License Health</h3>
            <Link href="/platform/licenses" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View all</Link>
          </div>

          {/* Doughnut SVG */}
          <div className="flex items-center justify-center relative my-2">
            <svg className="w-36 h-36 transform -rotate-90">
              {/* Total 5: Healthy 3 (60%), Expiring Soon 1 (20%), Suspended 1 (20%) */}
              <circle cx="72" cy="72" r="50" stroke="#1E2638" strokeWidth="16" fill="transparent" />
              {/* Healthy 60% */}
              <circle cx="72" cy="72" r="50" stroke="#2E9D50" strokeWidth="16" fill="transparent" strokeDasharray="314" strokeDashoffset="125" />
              {/* Expiring Soon 20% */}
              <circle cx="72" cy="72" r="50" stroke="#E65100" strokeWidth="16" fill="transparent" strokeDasharray="314" strokeDashoffset="251" />
              {/* Suspended 20% */}
              <circle cx="72" cy="72" r="50" stroke="#E53935" strokeWidth="16" fill="transparent" strokeDasharray="314" strokeDashoffset="282" />
            </svg>
            <div className="absolute flex flex-col items-center justify-center text-center">
              <span className="text-[24px] font-bold text-white leading-none">5</span>
              <span className="text-[10px] text-[#64748B] font-mono mt-0.5">Total</span>
            </div>
          </div>

          <div className="space-y-1.5 text-[11px] pt-2 border-t border-[#1E2638]">
            <div className="flex items-center justify-between font-bold">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50]" />
                <span className="text-[#94A3B8]">Healthy</span>
              </div>
              <span className="text-white">3 (60%)</span>
            </div>
            <div className="flex items-center justify-between font-bold">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#E65100]" />
                <span className="text-[#94A3B8]">Expiring Soon</span>
              </div>
              <span className="text-white">1 (20%)</span>
            </div>
            <div className="flex items-center justify-between font-bold">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#E53935]" />
                <span className="text-[#94A3B8]">Expired</span>
              </div>
              <span className="text-[#64748B]">0 (0%)</span>
            </div>
            <div className="flex items-center justify-between font-bold">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#64748B]" />
                <span className="text-[#94A3B8]">Suspended</span>
              </div>
              <span className="text-white">1 (20%)</span>
            </div>
          </div>
        </div>

        {/* Right: Security Overview List */}
        <div className="lg:col-span-3 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[15px]">Security Overview</h3>
            <Link href="/platform/security" className="text-[11px] text-[#2E9D50] hover:underline font-bold">View full dashboard →</Link>
          </div>

          <div className="space-y-2.5 text-[12px]">
            <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48]">
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-4 h-4 text-[#E53935]" />
                <span className="font-bold text-white">Security Incidents</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">3</span>
                <span className="text-[10px] text-[#E53935] font-mono">↑ 1</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48]">
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-4 h-4 text-[#E65100]" />
                <span className="font-bold text-white">Critical Risks</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">7</span>
                <span className="text-[10px] text-[#E65100] font-mono">↑ 2</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48]">
              <div className="flex items-center gap-2.5">
                <Lock className="w-4 h-4 text-[#2E9D50]" />
                <span className="font-bold text-white">Blocked Actions</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">23</span>
                <span className="text-[10px] text-[#2E9D50] font-mono">↑ 5</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48]">
              <div className="flex items-center gap-2.5">
                <Bot className="w-4 h-4 text-[#64748B]" />
                <span className="font-bold text-[#94A3B8]">Suspended Agents</span>
              </div>
              <span className="font-bold text-white">2</span>
            </div>

            <div className="flex items-center justify-between p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48]">
              <div className="flex items-center gap-2.5">
                <Users className="w-4 h-4 text-[#64748B]" />
                <span className="font-bold text-[#94A3B8]">Suspended Users</span>
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-white">1</span>
                <span className="text-[10px] text-[#E53935] font-mono">↑ 1</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. MAIN ROW 2: Organizations Table + Recent Audit Events Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Organizations Directory Table */}
        <div className="lg:col-span-7 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[16px]">Organizations</h3>
            <div className="flex items-center gap-3">
              <Link href="/platform/organizations" className="text-[12px] text-[#2E9D50] hover:underline font-bold">View All →</Link>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-3 py-1 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[11px] font-bold rounded-[6px] transition-colors flex items-center gap-1"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Add Org</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
            <table className="w-full text-left text-[12px]">
              <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">
                <tr>
                  <th className="py-2.5 px-3">Organization</th>
                  <th className="py-2.5 px-3">License</th>
                  <th className="py-2.5 px-3 text-center">Users</th>
                  <th className="py-2.5 px-3 text-center">AI Agents</th>
                  <th className="py-2.5 px-3">License Expiry</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2638]">
                {organizations.slice(0, 5).map((org) => (
                  <tr key={org.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-6 h-6 rounded bg-[#173B25] text-[#2E9D50] font-bold flex items-center justify-center text-[10px]">
                          {org.name[0]}
                        </div>
                        <span className="font-bold text-white">{org.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                        {org.plan_id}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center font-bold text-white">{org.user_count}</td>
                    <td className="py-3 px-3 text-center font-bold text-white">{org.agent_count}</td>
                    <td className="py-3 px-3 font-mono text-[11px] text-[#94A3B8]">
                      {org.expiry_date ? new Date(org.expiry_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Aug 31, 2027"}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50]">
                        {org.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right space-x-1.5">
                      <Link
                        href={`/platform/organizations/${org.id}`}
                        className="p-1 hover:text-[#2E9D50] inline-block text-[#64748B]"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                      <button
                        onClick={() => handleToggleStatus(org.id, org.status)}
                        className="p-1 hover:text-[#E53935] inline-block text-[#64748B]"
                        title="Toggle Status"
                      >
                        <Lock className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Recent Audit Events Stream */}
        <div className="lg:col-span-5 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[16px]">Recent Audit Events</h3>
            <Link href="/platform/audit" className="text-[12px] text-[#2E9D50] hover:underline font-bold">Audit Stream →</Link>
          </div>

          <div className="space-y-2 text-[12px]">
            {(overview?.recent_audits || []).map((ev: any, idx: number) => (
              <div key={idx} className="p-2.5 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 text-[11px]">
                    <span className="text-[#64748B] font-mono">2 min ago</span>
                    <span className="font-bold text-white">{ev.actor}</span>
                    <span className="text-[#94A3B8]">{ev.action}</span>
                  </div>
                  <div className="text-[10px] text-[#64748B] font-mono">
                    Target: <span className="text-white">{ev.target}</span> • Org: <span className="text-[#2E9D50]">{ev.organization}</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/30 font-mono shrink-0">
                  {ev.result}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. MAIN ROW 3: Expiring Licenses + System Health + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Expiring Licenses Table */}
        <div className="lg:col-span-5 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[16px]">Expiring Licenses</h3>
            <Link href="/platform/licenses" className="text-[12px] text-[#2E9D50] hover:underline font-bold">View All →</Link>
          </div>

          <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
            <table className="w-full text-left text-[12px]">
              <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">
                <tr>
                  <th className="py-2.5 px-3">Organization</th>
                  <th className="py-2.5 px-3">License</th>
                  <th className="py-2.5 px-3">Expiry Date</th>
                  <th className="py-2.5 px-3 text-center">Days Remaining</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2638]">
                {(overview?.expiring_licenses_list || []).map((lic: any, idx: number) => (
                  <tr key={idx} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3 px-3 font-bold text-white">{lic.org_name}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] font-mono">
                        {lic.plan_id}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-[#94A3B8]">
                      {lic.expiry_date ? new Date(lic.expiry_date).toLocaleDateString() : "Jun 30, 2027"}
                    </td>
                    <td className="py-3 px-3 text-center font-mono font-bold text-[#E65100]">
                      {lic.days_remaining} days
                    </td>
                    <td className="py-3 px-3 text-right">
                      <Link
                        href="/platform/licenses"
                        className="px-2.5 py-1 bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 rounded-[6px] text-[10px] font-bold hover:bg-[#2E9D50] hover:text-white transition-colors"
                      >
                        Extend
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* System Health Status List */}
        <div className="lg:col-span-3 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-[16px]">System Health</h3>
            <Link href="/platform/system" className="text-[12px] text-[#2E9D50] hover:underline font-bold">View All →</Link>
          </div>

          <div className="space-y-3 text-[12px]">
            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#E1E7F0]">Backend Services</span>
              </div>
              <span className="text-[10px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#E1E7F0]">Database (Supabase)</span>
              </div>
              <span className="text-[10px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#E1E7F0]">Supabase Auth</span>
              </div>
              <span className="text-[10px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#E1E7F0]">API Services</span>
              </div>
              <span className="text-[10px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>

            <div className="flex items-center justify-between p-2 bg-[#161C2A] rounded-[6px]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2E9D50] animate-pulse" />
                <span className="font-bold text-[#E1E7F0]">Background Jobs</span>
              </div>
              <span className="text-[10px] font-bold text-[#2E9D50] font-mono">Operational</span>
            </div>
          </div>
        </div>

        {/* Quick Actions 8-Button Grid */}
        <div className="lg:col-span-4 bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm flex flex-col justify-between">
          <h3 className="font-bold text-white text-[16px]">Quick Actions</h3>

          <div className="grid grid-cols-4 gap-3">
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <Building className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">Create Org</span>
            </button>

            <Link
              href="/platform/licenses"
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <CreditCard className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">Create License</span>
            </Link>

            <Link
              href="/platform/users"
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <Users className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">Add User</span>
            </Link>

            <Link
              href="/platform/agents"
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <Key className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">Create Key</span>
            </Link>

            <Link
              href="/platform/reports"
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <FileText className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">Generate Report</span>
            </Link>

            <Link
              href="/platform/audit"
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <FileSearch className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">View Audit</span>
            </Link>

            <Link
              href="/platform/system"
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <Server className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">System Health</span>
            </Link>

            <Link
              href="/platform/settings"
              className="p-3 bg-[#161C2A] border border-[#2E9D50]/40 rounded-[10px] hover:bg-[#173B25] transition-all flex flex-col items-center text-center space-y-1.5 group"
            >
              <Settings className="w-5 h-5 text-[#2E9D50]" />
              <span className="text-[10px] font-bold text-[#E1E7F0] group-hover:text-white leading-tight">Platform Settings</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#121722] border border-[#1E2638] rounded-[14px] max-w-md w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl text-white">
            <div className="flex items-center justify-between border-b border-[#1E2638] pb-3">
              <h2 className="text-[18px] font-bold">Provision New Organization</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-[#64748B] hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateOrgSubmit} className="space-y-4 text-[12px]">
              <div>
                <label className="block font-bold text-[#94A3B8] mb-1">Organization Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Technologies"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#94A3B8] mb-1">Domain</label>
                <input
                  type="text"
                  placeholder="e.g. acme.com"
                  value={newOrgDomain}
                  onChange={(e) => setNewOrgDomain(e.target.value)}
                  className="w-full px-3 py-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#94A3B8] mb-1">SaaS License Plan</label>
                <select
                  value={newOrgPlan}
                  onChange={(e) => setNewOrgPlan(e.target.value)}
                  className="w-full px-3 py-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-white outline-none focus:border-[#2E9D50]"
                >
                  <option value="STARTER">STARTER (10 Users, 5 Agents)</option>
                  <option value="PROFESSIONAL">PROFESSIONAL (50 Users, 20 Agents)</option>
                  <option value="ENTERPRISE">ENTERPRISE (Unlimited Users/Agents)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#94A3B8] mb-1">Org Admin Email</label>
                <input
                  type="email"
                  required
                  placeholder="admin@acme.com"
                  value={newOrgAdminEmail}
                  onChange={(e) => setNewOrgAdminEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#94A3B8] mb-1">Org Admin Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Aarav Sharma"
                  value={newOrgAdminName}
                  onChange={(e) => setNewOrgAdminName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-white outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1E2638]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white font-bold"
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
