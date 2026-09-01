"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Globe,
  ShieldAlert,
  Server,
  Building,
  Users,
  Bot,
  CreditCard,
  PlusCircle,
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  RefreshCw,
  Search,
  ExternalLink,
  Lock,
  UserCheck,
  Calendar,
  Layers,
  ArrowRight
} from "lucide-react";

export default function PlatformAdminPage() {
  const [activeTab, setActiveTab] = useState<"organizations" | "users" | "licenses">("organizations");

  const [overview, setOverview] = useState<any>(null);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [platformUsers, setPlatformUsers] = useState<any[]>([]);
  const [platformLicenses, setPlatformLicenses] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [userSearch, setUserSearch] = useState("");

  // Create Org Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgDomain, setNewOrgDomain] = useState("");
  const [newOrgPlan, setNewOrgPlan] = useState("STARTER");
  const [newOrgAdminEmail, setNewOrgAdminEmail] = useState("");
  const [newOrgAdminName, setNewOrgAdminName] = useState("");
  const [createMsg, setCreateMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // License Edit / Extend state
  const [selectedOrg, setSelectedOrg] = useState<any>(null);
  const [editPlanId, setEditPlanId] = useState("STARTER");
  const [editMaxUsers, setEditMaxUsers] = useState<number>(10);
  const [editMaxAgents, setEditMaxAgents] = useState<number>(5);

  const [selectedLicense, setSelectedLicense] = useState<any>(null);
  const [extendDays, setExtendDays] = useState<number>(30);

  const loadData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [ovData, orgsData, usersData, licData, plansData] = await Promise.all([
        fetchApi("/platform/overview"),
        fetchApi("/platform/organizations"),
        fetchApi("/platform/users").catch(() => []),
        fetchApi("/platform/licenses").catch(() => []),
        fetchApi("/platform/plans").catch(() => []),
      ]);
      setOverview(ovData);
      setOrganizations(orgsData || []);
      setPlatformUsers(usersData || []);
      setPlatformLicenses(licData || []);
      setPlans(plansData || []);
    } catch (err: any) {
      console.error("Platform data fetch error:", err);
      setErrorMsg(err.message || "Unable to load platform administration metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const handleContextChange = () => loadData();
    window.addEventListener("org-context-changed", handleContextChange);
    return () => window.removeEventListener("org-context-changed", handleContextChange);
  }, []);

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateMsg("");
    setSubmitting(true);
    try {
      const idempotencyKey = `create-org-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const res = await fetchApi("/platform/organizations", {
        method: "POST",
        headers: {
          "Idempotency-Key": idempotencyKey
        },
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
        loadData();
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
      loadData();
    } catch (err: any) {
      alert("Status change failed: " + err.message);
    }
  };

  const handleToggleUserStatus = async (userId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
    try {
      await fetchApi(`/platform/users/${userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus })
      });
      loadData();
    } catch (err: any) {
      alert("User status change failed: " + err.message);
    }
  };

  const handleUpdateUserRole = async (userId: string, newRole: string) => {
    try {
      await fetchApi(`/platform/users/${userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole })
      });
      loadData();
    } catch (err: any) {
      alert("Role update failed: " + err.message);
    }
  };

  const handleUpdateLicense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    try {
      await fetchApi(`/platform/organizations/${selectedOrg.id}/license`, {
        method: "PATCH",
        body: JSON.stringify({
          plan_id: editPlanId,
          max_users: editMaxUsers,
          max_ai_agents: editMaxAgents
        })
      });
      setSelectedOrg(null);
      loadData();
    } catch (err: any) {
      alert("License update failed: " + err.message);
    }
  };

  const handleExtendLicense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLicense) return;
    try {
      await fetchApi(`/platform/licenses/extend`, {
        method: "POST",
        body: JSON.stringify({
          org_id: selectedLicense.org_id,
          days: extendDays
        })
      });
      setSelectedLicense(null);
      loadData();
    } catch (err: any) {
      alert("License extension failed: " + err.message);
    }
  };

  const handleRenewLicense = async (orgId: string) => {
    if (!confirm("Renew annual subscription for 365 days?")) return;
    try {
      await fetchApi(`/platform/licenses/renew`, {
        method: "POST",
        body: JSON.stringify({ org_id: orgId })
      });
      loadData();
    } catch (err: any) {
      alert("License renewal failed: " + err.message);
    }
  };

  const handleRevokeLicense = async (orgId: string) => {
    if (!confirm("Revoke SaaS license for this organization?")) return;
    try {
      await fetchApi(`/platform/licenses/revoke`, {
        method: "POST",
        body: JSON.stringify({ org_id: orgId, reason: "Administrative Revocation" })
      });
      loadData();
    } catch (err: any) {
      alert("License revocation failed: " + err.message);
    }
  };

  const filteredOrgs = organizations.filter((o) =>
    o.name.toLowerCase().includes(search.toLowerCase()) ||
    (o.admin_email || "").toLowerCase().includes(search.toLowerCase()) ||
    (o.plan_id || "").toLowerCase().includes(search.toLowerCase())
  );

  const filteredUsers = platformUsers.filter((u) =>
    u.full_name.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.org_name.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.role.toLowerCase().includes(userSearch.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[#E8E8E4] pb-5 gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Globe className="w-6 h-6 text-[#8064C8]" />
            <h1 className="text-[20px] sm:text-[24px] font-bold text-[#1F1F1F]">Platform Administration</h1>
            <span className="bg-[#F1EDFA] text-[#8064C8] text-[10px] sm:text-[11px] font-bold px-2.5 py-0.5 rounded border border-[#8064C8]/30 uppercase">
              Super Admin Control Plane
            </span>
          </div>
          <p className="text-[12px] sm:text-[13px] text-[#666666] mt-1">
            Global Multi-Tenant Organization Management, SaaS Subscription Licensing, & Infrastructure Health
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0 flex-wrap">
          <button
            onClick={() => loadData()}
            className="flex items-center gap-2 px-3 py-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] text-[12px] sm:text-[13px] font-bold text-[#1F1F1F] hover:bg-[#FCFCFA] transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Metrics</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[12px] sm:text-[13px] font-bold transition-colors shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Organization</span>
          </button>
        </div>
      </div>

      {createMsg && (
        <div className="p-4 rounded-[8px] bg-[#EAF7EE] border border-[#2E9D50]/30 text-[#237A3C] text-[13px] font-bold flex items-center justify-between">
          <span>{createMsg}</span>
          <button onClick={() => setCreateMsg("")} className="text-[11px] text-[#2E9D50] underline">Dismiss</button>
        </div>
      )}

      {errorMsg && (
        <div className="p-5 rounded-[12px] bg-[#FDECEC] border border-[#E53935]/30 space-y-3 shadow-sm">
          <div className="flex items-center gap-3 text-[#E53935]">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <h3 className="font-bold text-[14px]">Unable to load platform administration metrics</h3>
          </div>
          <p className="text-[12px] text-[#666666]">{errorMsg}</p>
          <button
            onClick={() => loadData()}
            className="px-3 py-1.5 bg-[#E53935] text-white text-[12px] font-bold rounded-[6px] hover:bg-[#C62828] transition-colors"
          >
            Retry API Request
          </button>
        </div>
      )}

      {/* Platform Overview Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase">Tenant Organizations</span>
            <Building className="w-5 h-5 text-[#8064C8]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#FCFCFA] animate-pulse rounded w-20" />
          ) : (
            <div className="flex items-baseline gap-2">
              <h2 className="text-[28px] font-bold text-[#1F1F1F]">
                {overview?.total_organizations ?? 0}
              </h2>
              <span className="text-[12px] font-bold text-[#237A3C]">
                ({overview?.active_organizations ?? 0} Active)
              </span>
            </div>
          )}
          <span className="text-[11px] text-[#666666] block">
            {overview?.suspended_organizations ?? 0} Suspended / Restricted
          </span>
        </div>

        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase">Platform Users</span>
            <Users className="w-5 h-5 text-[#0284C7]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#FCFCFA] animate-pulse rounded w-20" />
          ) : (
            <h2 className="text-[28px] font-bold text-[#1F1F1F]">
              {overview?.total_users ?? 0}
            </h2>
          )}
          <span className="text-[11px] text-[#666666] block">Across All Tenant Workspaces</span>
        </div>

        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase">Governed AI Agents</span>
            <Bot className="w-5 h-5 text-[#2E9D50]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#FCFCFA] animate-pulse rounded w-20" />
          ) : (
            <h2 className="text-[28px] font-bold text-[#1F1F1F]">
              {overview?.total_ai_agents ?? 0}
            </h2>
          )}
          <span className="text-[11px] text-[#2E9D50] font-bold block">100% Circuit Breaker Protected</span>
        </div>

        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase">Active SaaS Licenses</span>
            <CreditCard className="w-5 h-5 text-[#E65100]" />
          </div>
          {loading ? (
            <div className="h-8 bg-[#FCFCFA] animate-pulse rounded w-20" />
          ) : (
            <h2 className="text-[28px] font-bold text-[#1F1F1F]">
              {overview?.active_licenses ?? 0}
            </h2>
          )}
          <span className="text-[11px] text-[#666666] block">
            {overview?.expiring_licenses ?? 0} Expiring Soon
          </span>
        </div>
      </div>

      {/* Control Plane Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-[#E8E8E4] pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab("organizations")}
          className={`flex items-center gap-2 px-4 py-2 rounded-[8px] text-[13px] font-bold transition-colors ${
            activeTab === "organizations"
              ? "bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30"
              : "text-[#666666] hover:bg-[#FCFCFA] hover:text-[#1F1F1F]"
          }`}
        >
          <Building className="w-4 h-4" />
          <span>Tenant Organizations ({organizations.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("users")}
          className={`flex items-center gap-2 px-4 py-2 rounded-[8px] text-[13px] font-bold transition-colors ${
            activeTab === "users"
              ? "bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30"
              : "text-[#666666] hover:bg-[#FCFCFA] hover:text-[#1F1F1F]"
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Platform Users ({platformUsers.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("licenses")}
          className={`flex items-center gap-2 px-4 py-2 rounded-[8px] text-[13px] font-bold transition-colors ${
            activeTab === "licenses"
              ? "bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30"
              : "text-[#666666] hover:bg-[#FCFCFA] hover:text-[#1F1F1F]"
          }`}
        >
          <CreditCard className="w-4 h-4" />
          <span>SaaS Licenses ({platformLicenses.length})</span>
        </button>
      </div>

      {/* TAB 1: Organizations Management */}
      {activeTab === "organizations" && (
        <div className="space-y-6">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-[18px] font-bold text-[#1F1F1F]">Managed Tenant Organizations</h2>
                <p className="text-[12px] text-[#666666]">
                  Database multi-tenant isolation, organization admin assignments & subscription plans
                </p>
              </div>

              <div className="relative w-full sm:w-64">
                <Search className="w-4 h-4 text-[#666666] absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search organizations..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] outline-none focus:border-[#8064C8]"
                />
              </div>
            </div>

            <div className="overflow-x-auto border border-[#E8E8E4] rounded-[8px]">
              <table className="w-full text-left text-[13px]">
                <thead className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                  <tr>
                    <th className="py-3 px-4">Organization</th>
                    <th className="py-3 px-4">Plan / License</th>
                    <th className="py-3 px-4">Org Admin</th>
                    <th className="py-3 px-4 text-center">Users Limit</th>
                    <th className="py-3 px-4 text-center">Agents Limit</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E8E8E4]">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-[#666666]">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto text-[#8064C8] mb-2" />
                        Loading organization records...
                      </td>
                    </tr>
                  ) : filteredOrgs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-[#666666]">
                        No organizations match your search filter.
                      </td>
                    </tr>
                  ) : (
                    filteredOrgs.map((org) => (
                      <tr key={org.id} className="hover:bg-[#FCFCFA] transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-bold text-[#1F1F1F]">{org.name}</div>
                          <div className="text-[11px] font-mono text-[#666666]">{org.domain || org.slug || "no-domain.com"}</div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/20">
                            {org.plan_id}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[12px] text-[#1F1F1F]">
                          {org.admin_email}
                        </td>
                        <td className="py-3 px-4 text-center font-bold text-[#1F1F1F]">
                          {org.user_count} / {org.max_users}
                        </td>
                        <td className="py-3 px-4 text-center font-bold text-[#1F1F1F]">
                          {org.agent_count} / {org.max_ai_agents}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold uppercase ${
                              org.status === "ACTIVE"
                                ? "bg-[#EAF7EE] text-[#237A3C]"
                                : "bg-[#FDECEC] text-[#E53935]"
                            }`}
                          >
                            {org.status === "ACTIVE" ? (
                              <CheckCircle className="w-3 h-3" />
                            ) : (
                              <XCircle className="w-3 h-3" />
                            )}
                            {org.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right space-x-2 shrink-0">
                          <button
                            onClick={() => {
                              setSelectedOrg(org);
                              setEditPlanId(org.plan_id);
                              setEditMaxUsers(org.max_users);
                              setEditMaxAgents(org.max_ai_agents);
                            }}
                            className="px-2.5 py-1 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] text-[11px] font-bold text-[#8064C8] hover:bg-[#F1EDFA] transition-colors"
                          >
                            Edit License
                          </button>

                          <button
                            onClick={() => handleToggleStatus(org.id, org.status)}
                            className={`px-2.5 py-1 rounded-[6px] text-[11px] font-bold border transition-colors ${
                              org.status === "ACTIVE"
                                ? "bg-[#FFFFFF] border-[#E8E8E4] text-[#E53935] hover:bg-[#FDECEC]"
                                : "bg-[#2E9D50] text-white border-transparent hover:bg-[#237A3C]"
                            }`}
                          >
                            {org.status === "ACTIVE" ? "Suspend" : "Activate"}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Available SaaS Plans Grid */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Platform SaaS Subscription Plans</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {plans.map((p) => (
                <div key={p.id} className="border border-[#E8E8E4] rounded-[10px] p-4 space-y-3 bg-[#FCFCFA]">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#8064C8] text-[12px] uppercase tracking-wider">{p.id}</span>
                    <span className="text-[14px] font-bold text-[#1F1F1F]">
                      ${p.price_monthly} <span className="text-[10px] text-[#666666] font-normal">/mo</span>
                    </span>
                  </div>
                  <h3 className="font-bold text-[#1F1F1F] text-[15px]">{p.name}</h3>
                  <p className="text-[11px] text-[#666666] leading-tight">{p.description}</p>
                  <div className="pt-2 border-t border-[#E8E8E4] space-y-1 text-[11px] font-bold text-[#1F1F1F]">
                    <div>• Max Users: {p.max_users}</div>
                    <div>• Max AI Agents: {p.max_ai_agents}</div>
                    <div>• Max API Requests: {p.max_monthly_api_requests.toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: User Management */}
      {activeTab === "users" && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-5 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-[18px] font-bold text-[#1F1F1F]">Platform User Directory</h2>
              <p className="text-[12px] text-[#666666]">
                Global user accounts across all tenant organizations & administrative roles
              </p>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-[#666666] absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search users..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] outline-none focus:border-[#8064C8]"
              />
            </div>
          </div>

          <div className="overflow-x-auto border border-[#E8E8E4] rounded-[8px]">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Tenant Organization</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E8E4]">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-[#666666]">
                      No platform users match your search.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-[#FCFCFA] transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-[#1F1F1F]">{u.full_name}</div>
                        <div className="text-[11px] font-mono text-[#666666]">{u.email}</div>
                      </td>
                      <td className="py-3 px-4 font-bold text-[#1F1F1F]">
                        {u.org_name}
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/20 font-mono">
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-[#666666]">{u.department}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold uppercase ${
                            u.status === "ACTIVE"
                              ? "bg-[#EAF7EE] text-[#237A3C]"
                              : "bg-[#FDECEC] text-[#E53935]"
                          }`}
                        >
                          {u.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => handleToggleUserStatus(u.id, u.status)}
                          className={`px-2.5 py-1 rounded-[6px] text-[11px] font-bold border transition-colors ${
                            u.status === "ACTIVE"
                              ? "bg-[#FFFFFF] border-[#E8E8E4] text-[#E53935] hover:bg-[#FDECEC]"
                              : "bg-[#2E9D50] text-white border-transparent hover:bg-[#237A3C]"
                          }`}
                        >
                          {u.status === "ACTIVE" ? "Suspend" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SaaS Licenses */}
      {activeTab === "licenses" && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-5 shadow-sm">
          <div>
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Active SaaS License Inventory</h2>
            <p className="text-[12px] text-[#666666]">
              Tenant subscription plans, seat quotas, AI agent caps, and annual expiration dates
            </p>
          </div>

          <div className="overflow-x-auto border border-[#E8E8E4] rounded-[8px]">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <tr>
                  <th className="py-3 px-4">Tenant Organization</th>
                  <th className="py-3 px-4">Plan</th>
                  <th className="py-3 px-4 text-center">User Seats</th>
                  <th className="py-3 px-4 text-center">Agent Cap</th>
                  <th className="py-3 px-4">Expiry Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E8E4]">
                {platformLicenses.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-[#666666]">
                      No active licenses found.
                    </td>
                  </tr>
                ) : (
                  platformLicenses.map((lic) => (
                    <tr key={lic.id} className="hover:bg-[#FCFCFA] transition-colors">
                      <td className="py-3 px-4 font-bold text-[#1F1F1F]">
                        {lic.org_name}
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/20">
                          {lic.plan_id}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-bold text-[#1F1F1F]">
                        {lic.user_count} / {lic.max_users}
                      </td>
                      <td className="py-3 px-4 text-center font-bold text-[#1F1F1F]">
                        {lic.agent_count} / {lic.max_ai_agents}
                      </td>
                      <td className="py-3 px-4 font-mono text-[12px]">
                        {lic.expiry_date ? new Date(lic.expiry_date).toLocaleDateString() : "Lifetime / No Expiry"}
                        {lic.expiring_soon && (
                          <span className="ml-2 text-[10px] font-bold text-[#E65100] uppercase bg-[#FFF3E0] px-1.5 py-0.5 rounded">
                            {lic.days_remaining}d left
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold uppercase ${
                            lic.status === "ACTIVE"
                              ? "bg-[#EAF7EE] text-[#237A3C]"
                              : "bg-[#FDECEC] text-[#E53935]"
                          }`}
                        >
                          {lic.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => setSelectedLicense(lic)}
                          className="px-2.5 py-1 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] text-[11px] font-bold text-[#2E9D50] hover:bg-[#EAF7EE] transition-colors"
                        >
                          Extend
                        </button>
                        <button
                          onClick={() => handleRenewLicense(lic.org_id)}
                          className="px-2.5 py-1 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] text-[11px] font-bold text-[#0284C7] hover:bg-[#E0F2FE] transition-colors"
                        >
                          Renew 1Yr
                        </button>
                        <button
                          onClick={() => handleRevokeLicense(lic.org_id)}
                          className="px-2.5 py-1 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] text-[11px] font-bold text-[#E53935] hover:bg-[#FDECEC] transition-colors"
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] max-w-md w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-xl">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Provision New Organization</h2>
            <form onSubmit={handleCreateOrg} className="space-y-4 text-[13px]">
              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Organization Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Technologies"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Domain</label>
                <input
                  type="text"
                  placeholder="e.g. acme.com"
                  value={newOrgDomain}
                  onChange={(e) => setNewOrgDomain(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">SaaS License Plan</label>
                <select
                  value={newOrgPlan}
                  onChange={(e) => setNewOrgPlan(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.id} ({p.max_users} Users, {p.max_ai_agents} Agents)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Organization ADMIN Email</label>
                <input
                  type="email"
                  required
                  placeholder="admin@acme.com"
                  value={newOrgAdminEmail}
                  onChange={(e) => setNewOrgAdminEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Admin Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Acme Admin"
                  value={newOrgAdminName}
                  onChange={(e) => setNewOrgAdminName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-[#E8E8E4] rounded-[8px] font-bold text-[#666666] hover:bg-[#FCFCFA]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] font-bold"
                >
                  {submitting ? "Provisioning..." : "Provision Tenant"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit License Limits Modal */}
      {selectedOrg && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] max-w-md w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-xl">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Edit License — {selectedOrg.name}</h2>
            <form onSubmit={handleUpdateLicense} className="space-y-4 text-[13px]">
              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Plan</label>
                <select
                  value={editPlanId}
                  onChange={(e) => {
                    setEditPlanId(e.target.value);
                    const selected = plans.find((p) => p.id === e.target.value);
                    if (selected) {
                      setEditMaxUsers(selected.max_users);
                      setEditMaxAgents(selected.max_ai_agents);
                    }
                  }}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#8064C8]"
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.id} — {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Max Users Limit</label>
                <input
                  type="number"
                  required
                  value={editMaxUsers}
                  onChange={(e) => setEditMaxUsers(parseInt(e.target.value) || 1)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#8064C8]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Max AI Agents Limit</label>
                <input
                  type="number"
                  required
                  value={editMaxAgents}
                  onChange={(e) => setEditMaxAgents(parseInt(e.target.value) || 1)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#8064C8]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setSelectedOrg(null)}
                  className="px-4 py-2 border border-[#E8E8E4] rounded-[8px] font-bold text-[#666666] hover:bg-[#FCFCFA]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#8064C8] hover:bg-[#6C4EB8] text-white rounded-[8px] font-bold"
                >
                  Save License Updates
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Extend License Days Modal */}
      {selectedLicense && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] max-w-md w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-xl">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Extend License — {selectedLicense.org_name}</h2>
            <form onSubmit={handleExtendLicense} className="space-y-4 text-[13px]">
              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Days to Extend</label>
                <input
                  type="number"
                  required
                  min={1}
                  max={365}
                  value={extendDays}
                  onChange={(e) => setExtendDays(parseInt(e.target.value) || 30)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setSelectedLicense(null)}
                  className="px-4 py-2 border border-[#E8E8E4] rounded-[8px] font-bold text-[#666666] hover:bg-[#FCFCFA]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] font-bold"
                >
                  Extend Subscription
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
