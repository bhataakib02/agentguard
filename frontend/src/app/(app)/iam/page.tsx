"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import StatusBadge from "@/components/ui/StatusBadge";
import { Users, Shield, Search, Filter, AlertTriangle, Check, X, Lock, UserPlus, CreditCard } from "lucide-react";

const HUMAN_ROLES = [
  "USER",
  "VIEWER",
  "ANALYST",
  "OPERATOR",
  "SECURITY_ANALYST",
  "MANAGER",
  "DEVELOPER",
  "ADMIN",
  "SUPER_ADMIN"
];

const INVITEABLE_ROLES = [
  "USER",
  "VIEWER",
  "ANALYST",
  "OPERATOR",
  "SECURITY_ANALYST",
  "MANAGER",
  "DEVELOPER",
  "ADMIN"
];

interface PendingRoleChange {
  userId: string;
  userName: string;
  oldRole: string;
  newRole: string;
}

export default function IamPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [orgMetrics, setOrgMetrics] = useState<any>(null);

  // Invite Modal state
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("USER");
  const [inviteDept, setInviteDept] = useState("General");
  const [inviteMsg, setInviteMsg] = useState("");
  const [inviting, setInviting] = useState(false);

  // Modal State
  const [pendingChange, setPendingChange] = useState<PendingRoleChange | null>(null);
  const [updating, setUpdating] = useState(false);
  const [notice, setNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const queryParams = new URLSearchParams();
      if (search) queryParams.set("search", search);
      if (roleFilter !== "ALL") queryParams.set("role_filter", roleFilter);
      if (statusFilter !== "ALL") queryParams.set("status_filter", statusFilter);

      const [uData, rData, orgDash] = await Promise.all([
        fetchApi(`/admin/users?${queryParams.toString()}`).catch(() => fetchApi("/iam/users")),
        fetchApi("/iam/roles").catch(() => []),
        fetchApi("/organization/dashboard").catch(() => null)
      ]);
      setUsers(uData || []);
      setRoles(rData || []);
      setOrgMetrics(orgDash);
    } catch (err: any) {
      console.error("IAM load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [roleFilter, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  const initiateRoleChange = (targetUser: any, newRole: string) => {
    if (targetUser.role === newRole) return;

    if (currentUser && targetUser.id === currentUser.id) {
      setNotice({
        type: "error",
        message: "Forbidden: You cannot modify your own role."
      });
      return;
    }

    if (newRole === "SUPER_ADMIN" && currentUser?.role !== "SUPER_ADMIN") {
      setNotice({
        type: "error",
        message: "Forbidden: Only an existing SUPER_ADMIN can assign the SUPER_ADMIN role."
      });
      return;
    }

    setPendingChange({
      userId: targetUser.id,
      userName: targetUser.full_name,
      oldRole: targetUser.role,
      newRole
    });
  };

  const confirmRoleChange = async () => {
    if (!pendingChange) return;
    setUpdating(true);
    setNotice(null);

    try {
      await fetchApi(`/admin/users/${pendingChange.userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: pendingChange.newRole }),
      });

      setNotice({
        type: "success",
        message: `Successfully changed ${pendingChange.userName}'s role from ${pendingChange.oldRole} to ${pendingChange.newRole}`
      });
      setPendingChange(null);
      await loadData();
    } catch (err: any) {
      setNotice({
        type: "error",
        message: err.message || "Failed to update user role"
      });
    } finally {
      setUpdating(false);
    }
  };

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteMsg("");
    setInviting(true);

    try {
      const res = await fetchApi("/organization/invite-user", {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail,
          full_name: inviteName,
          role: inviteRole,
          department: inviteDept,
          password: "Blackbird@12."
        })
      });

      if (res.status === "SUCCESS") {
        setNotice({
          type: "success",
          message: `User ${inviteEmail} successfully invited with role ${inviteRole}.`
        });
        setShowInviteModal(false);
        setInviteEmail("");
        setInviteName("");
        loadData();
      }
    } catch (err: any) {
      setInviteMsg(err.message || "Failed to invite user.");
    } finally {
      setInviting(false);
    }
  };

  const availableRoles = currentUser?.role === "SUPER_ADMIN"
    ? HUMAN_ROLES
    : HUMAN_ROLES.filter(r => r !== "SUPER_ADMIN");

  const userMetrics = orgMetrics?.metrics?.users || { current: users.length, max: 10 };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#E8E8E4] pb-5 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-6 h-6 text-[#8064C8]" />
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">IAM Users & Organization Roles</h1>
          </div>
          <p className="text-[13px] text-[#666666] mt-1">
            Real Database User Management, 9-Tier Human Organization Roles, & License Limit Enforcement
          </p>
        </div>

        {["ADMIN", "SUPER_ADMIN"].includes(currentUser?.role || "") && (
          <button
            onClick={() => setShowInviteModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold transition-colors shadow-sm self-start sm:self-auto"
          >
            <UserPlus className="w-4 h-4" />
            <span>Invite Team User</span>
          </button>
        )}
      </div>

      {/* License Meter Banner */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <CreditCard className="w-5 h-5 text-[#8064C8]" />
          <div>
            <span className="text-[12px] font-bold text-[#1F1F1F] block">
              Tenant User License Allocation: {userMetrics.current} / {userMetrics.max} Seats Used
            </span>
            <span className="text-[11px] text-[#666666]">
              Subscription Plan: <strong className="text-[#8064C8]">{orgMetrics?.plan_id || "STARTER"}</strong> (Backend Metered Enforcement)
            </span>
          </div>
        </div>

        <div className="w-full sm:w-48 bg-[#FCFCFA] border border-[#E8E8E4] h-2.5 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#8064C8] transition-all"
            style={{ width: `${Math.min(100, (userMetrics.current / userMetrics.max) * 100)}%` }}
          />
        </div>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div className={`p-4 rounded-[8px] border text-[13px] font-bold flex items-center justify-between ${
          notice.type === "success"
            ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
            : "bg-[#FDECEC] text-[#E53935] border-[#E53935]/30"
        }`}>
          <span>{notice.message}</span>
          <button onClick={() => setNotice(null)} className="text-[#666666] hover:text-[#1F1F1F]">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-4 flex flex-col md:flex-row gap-4 items-center justify-between shadow-sm">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-[#666666] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search name, email, department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] outline-none focus:border-[#1F1F1F]"
          />
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-[12px] text-[#666666]">
            <Filter className="w-3.5 h-3.5" />
            <span>Role:</span>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-2 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[12px] font-bold text-[#1F1F1F]"
            >
              <option value="ALL">All Roles</option>
              {HUMAN_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-[12px] text-[#666666]">
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[12px] font-bold text-[#1F1F1F]"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
              <option value="SUSPENDED">SUSPENDED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      {users.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Users className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">No Matching Users</h3>
          <p className="text-[12px] text-[#666666]">
            No user accounts found matching your query filters.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">NAME & EMAIL</th>
                <th className="p-4">ORGANIZATION</th>
                <th className="p-4">CURRENT ROLE</th>
                <th className="p-4">DEPARTMENT</th>
                <th className="p-4">ACCOUNT STATUS</th>
                <th className="p-4 text-right">ROLE ASSIGNMENT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {users.map((u) => {
                const isSelf = currentUser && u.id === currentUser.id;
                return (
                  <tr key={u.id} className="hover:bg-[#FCFCFA] transition-colors">
                    <td className="p-4 space-y-0.5">
                      <div className="font-bold text-[#1F1F1F] flex items-center gap-2">
                        <span>{u.full_name}</span>
                        {isSelf && <span className="text-[10px] bg-[#F1EDFA] text-[#8064C8] font-bold px-1.5 py-0.2 rounded">(You)</span>}
                      </div>
                      <div className="text-[#666666] font-mono text-[11px]">{u.email}</div>
                    </td>
                    <td className="p-4 text-[#666666] font-bold text-[12px]">
                      {u.org_name || "AgentGuard Enterprise"}
                    </td>
                    <td className="p-4">
                      <span className={`inline-block px-2.5 py-1 rounded-[6px] text-[11px] font-bold ${
                        u.role === "SUPER_ADMIN"
                          ? "bg-[#1F1F1F] text-[#FFFFFF]"
                          : u.role === "ADMIN"
                          ? "bg-[#FDECEC] text-[#C62828] border border-[#E53935]/30"
                          : u.role === "SECURITY_ANALYST"
                          ? "bg-[#FFF4D9] text-[#F59A23] border border-[#F59A23]/30"
                          : u.role === "MANAGER"
                          ? "bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/30"
                          : u.role === "DEVELOPER"
                          ? "bg-[#E0F2FE] text-[#0284C7] border border-[#0284C7]/30"
                          : "bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30"
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="p-4 text-[#666666]">
                      {u.department || "General"}
                    </td>
                    <td className="p-4"><StatusBadge status={u.status || "ACTIVE"} /></td>
                    <td className="p-4 text-right">
                      {isSelf ? (
                        <span className="text-[11px] text-[#666666] italic">Protected Self</span>
                      ) : (
                        <select
                          value={u.role}
                          onChange={(e) => initiateRoleChange(u, e.target.value)}
                          className="px-2.5 py-1.5 text-[12px] font-bold bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] focus:outline-none focus:border-[#1F1F1F] cursor-pointer hover:border-[#666666]"
                        >
                          {availableRoles.map((roleOption) => (
                            <option key={roleOption} value={roleOption}>
                              {roleOption}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Invite User Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] max-w-md w-full p-6 space-y-5 shadow-xl">
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Invite Organization Team User</h2>

            {inviteMsg && (
              <div className="p-3 rounded-[8px] bg-[#FDECEC] border border-[#E53935]/30 text-[#E53935] text-[12px] font-bold">
                {inviteMsg}
              </div>
            )}

            <form onSubmit={handleInviteUser} className="space-y-4 text-[13px]">
              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Jane Doe"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="jane.doe@organization.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Human Organization Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                >
                  {INVITEABLE_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <span className="text-[11px] text-[#666666] block mt-1">SUPER_ADMIN & AGENT roles excluded</span>
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Department</label>
                <input
                  type="text"
                  placeholder="e.g. AI Governance"
                  value={inviteDept}
                  onChange={(e) => setInviteDept(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 border border-[#E8E8E4] rounded-[8px] font-bold text-[#666666] hover:bg-[#FCFCFA]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting}
                  className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[8px]"
                >
                  {inviting ? "Inviting..." : "Send Invitation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Role Change Confirmation Modal */}
      {pendingChange && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] max-w-md w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center gap-3 text-[#E53935]">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-[18px] font-bold">Confirm Role Change</h3>
            </div>

            <p className="text-[13px] text-[#666666] leading-relaxed">
              Are you sure you want to change <strong>{pendingChange.userName}</strong>'s role from{" "}
              <strong className="text-[#1F1F1F]">{pendingChange.oldRole}</strong> to{" "}
              <strong className="text-[#8064C8]">{pendingChange.newRole}</strong>? This action updates database permissions immediately.
            </p>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setPendingChange(null)}
                disabled={updating}
                className="px-4 py-2 border border-[#E8E8E4] rounded-[8px] text-[13px] font-bold text-[#666666] hover:bg-[#FCFCFA]"
              >
                Cancel
              </button>

              <button
                onClick={confirmRoleChange}
                disabled={updating}
                className="px-4 py-2 bg-[#1F1F1F] hover:bg-[#333333] text-white rounded-[8px] text-[13px] font-bold transition-colors"
              >
                {updating ? "Updating..." : "Confirm Role Update"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
