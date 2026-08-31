"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { supabase } from "@/lib/supabase";
import StatusBadge from "@/components/ui/StatusBadge";
import {
  User,
  Shield,
  Lock,
  Key,
  Clock,
  Building,
  CheckCircle,
  AlertCircle,
  Activity,
  LogOut,
  Edit3,
  Check,
  X,
  Eye,
  EyeOff,
  Bell,
  Globe,
  Users,
  ShieldCheck,
  Zap,
  Mail,
  Smartphone,
  Info
} from "lucide-react";

export default function SettingsPage() {
  const { user, refreshProfile, logout } = useAuth();
  const [profileData, setProfileData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"account" | "security" | "notifications" | "organization">("account");
  const [loading, setLoading] = useState(true);

  // Edit State
  const [isEditing, setIsEditing] = useState(false);
  const [editFullName, setEditFullName] = useState("");
  const [editDepartment, setEditDepartment] = useState("");
  const [editJobTitle, setEditJobTitle] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [updating, setUpdating] = useState(false);
  const [notice, setNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Password State
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [passwordUpdating, setPasswordUpdating] = useState(false);

  // Verification & Sessions
  const [verifyingEmail, setVerifyingEmail] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);

  // Notifications Toggle State
  const [notifState, setNotifState] = useState({
    securityAlerts: true,
    governanceAlerts: true,
    approvalNotifs: true,
    systemNotifs: false,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await fetchApi("/profile/me");
      setProfileData(data);
      setEditFullName(data.full_name || "");
      setEditDepartment(data.department || "");
      setEditJobTitle(data.job_title || "");
      setEditPhone(data.phone || "");

      const [sessData, actData] = await Promise.all([
        fetchApi("/profile/sessions").catch(() => []),
        fetchApi("/profile/activity").catch(() => []),
      ]);
      setSessions(sessData || []);
      setActivities(actData || []);
    } catch (err) {
      console.error("Settings load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getInitials = (name?: string, email?: string) => {
    if (name && name.trim().length > 0) {
      const parts = name.trim().split(" ");
      if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      return parts[0].substring(0, 2).toUpperCase();
    }
    if (email) return email.substring(0, 2).toUpperCase();
    return "AG";
  };

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdating(true);
    setNotice(null);

    try {
      await fetchApi("/profile/me", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: editFullName,
          department: editDepartment,
          job_title: editJobTitle,
          phone: editPhone,
        }),
      });
      setNotice({ type: "success", message: "Account profile successfully updated!" });
      setIsEditing(false);
      await refreshProfile();
      await loadData();
    } catch (err: any) {
      setNotice({ type: "error", message: err.message || "Failed to update profile" });
    } finally {
      setUpdating(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setNotice({ type: "error", message: "New password and confirmation do not match." });
      return;
    }
    if (newPassword.length < 6) {
      setNotice({ type: "error", message: "Password must be at least 6 characters." });
      return;
    }

    setPasswordUpdating(true);
    setNotice(null);

    try {
      const { error: authErr } = await supabase.auth.updateUser({ password: newPassword });
      if (authErr) throw new Error(authErr.message);

      setNotice({ type: "success", message: "Password updated successfully in Supabase Auth!" });
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setNotice({ type: "error", message: err.message || "Failed to update password." });
    } finally {
      setPasswordUpdating(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  const handleResendVerification = async () => {
    if (!profileData?.email) return;
    setVerifyingEmail(true);
    setNotice(null);

    try {
      await fetchApi("/auth/resend-verification", {
        method: "POST",
        body: JSON.stringify({ email: profileData.email }),
      }).catch(() => null);

      const { error: resendErr } = await supabase.auth.resend({
        type: "signup",
        email: profileData.email,
      });

      if (resendErr) throw new Error(resendErr.message);
      setNotice({ type: "success", message: "Verification link sent to your email address." });
    } catch (err: any) {
      setNotice({ type: "error", message: err.message || "Failed to resend verification email." });
    } finally {
      setVerifyingEmail(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await fetchApi(`/profile/sessions/${sessionId}`, { method: "DELETE" });
      setNotice({ type: "success", message: "Session revoked successfully." });
      await loadData();
    } catch (err: any) {
      setNotice({ type: "error", message: err.message || "Failed to revoke session." });
    } finally {
      setTimeout(() => setNotice(null), 3000);
    }
  };

  const displayUser = profileData || user;
  const userRole = displayUser?.role || "USER";
  const initials = getInitials(displayUser?.full_name, displayUser?.email);

  if (loading && !profileData) {
    return (
      <div className="p-12 text-center text-[#666666] font-bold space-y-2">
        <Activity className="w-8 h-8 animate-spin mx-auto text-[#2E9D50]" />
        <p className="text-[13px]">Fetching real user settings from Supabase Auth...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[#E8E8E4] pb-5 gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-[12px] bg-[#1F1F1F] text-white flex items-center justify-center text-[22px] font-bold shadow-md shrink-0 border border-[#2E9D50]">
            {initials}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-[24px] font-bold text-[#1F1F1F]">{displayUser?.full_name || "Enterprise User"}</h1>
              <span className="text-[10px] font-bold px-2.5 py-0.5 bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/30 rounded-full uppercase">
                {userRole}
              </span>
            </div>
            <p className="text-[13px] text-[#666666] mt-0.5 font-mono">{displayUser?.email}</p>
          </div>
        </div>

        <Link
          href="/profile"
          className="px-4 py-2 bg-[#FFFFFF] border border-[#E8E8E4] text-[#1F1F1F] text-[13px] font-bold rounded-[8px] hover:bg-[#FCFCFA] flex items-center gap-2 transition-colors shrink-0 shadow-sm"
        >
          <User className="w-4 h-4 text-[#2E9D50]" />
          <span>View Profile</span>
        </Link>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div className={`p-4 rounded-[8px] text-[13px] font-bold border flex items-center gap-2 ${
          notice.type === "success"
            ? "bg-[#EAF7EE] border-[#2E9D50]/30 text-[#237A3C]"
            : "bg-[#FDECEC] border-[#E53935]/30 text-[#C62828]"
        }`}>
          {notice.type === "success" ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{notice.message}</span>
        </div>
      )}

      {/* Settings Tab Selector */}
      <div className="flex border-b border-[#E8E8E4] gap-6 text-[13px] font-bold">
        {[
          { id: "account", label: "ACCOUNT", icon: User },
          { id: "security", label: "SECURITY", icon: Shield },
          { id: "notifications", label: "NOTIFICATIONS", icon: Bell },
          { id: "organization", label: "ORGANIZATION", icon: Building },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 flex items-center gap-2 transition-colors border-b-2 ${
                isActive
                  ? "border-[#2E9D50] text-[#2E9D50]"
                  : "border-transparent text-[#666666] hover:text-[#1F1F1F]"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: ACCOUNT SETTINGS */}
      {activeTab === "account" && (
        <div className="space-y-6">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-6">
            <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">Account Profile Details</h3>
              {!isEditing && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="px-3 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[12px] font-bold text-[#1F1F1F] hover:bg-[#F0F0ED] flex items-center gap-1.5"
                >
                  <Edit3 className="w-3.5 h-3.5 text-[#2E9D50]" />
                  <span>Edit Profile</span>
                </button>
              )}
            </div>

            {isEditing ? (
              <form onSubmit={handleProfileSave} className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#666666] uppercase">Full Name</label>
                  <input
                    type="text"
                    required
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                    className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#666666] uppercase">Department</label>
                  <input
                    type="text"
                    value={editDepartment}
                    onChange={(e) => setEditDepartment(e.target.value)}
                    className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#666666] uppercase">Job Title</label>
                  <input
                    type="text"
                    value={editJobTitle}
                    onChange={(e) => setEditJobTitle(e.target.value)}
                    className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#666666] uppercase">Phone Number</label>
                  <input
                    type="text"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    placeholder="+1 (555) 000-0000"
                    className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
                  />
                </div>

                <div className="col-span-full pt-2 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="px-4 py-2 text-[12px] font-bold text-[#666666] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={updating}
                    className="px-4 py-2 text-[12px] font-bold text-[#FFFFFF] bg-[#2E9D50] hover:bg-[#237A3C] rounded-[6px]"
                  >
                    {updating ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              </form>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-[13px]">
                <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                  <span className="text-[10px] font-bold text-[#666666] uppercase block">Full Name</span>
                  <span className="font-bold text-[#1F1F1F]">{displayUser?.full_name || "N/A"}</span>
                </div>

                <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                  <span className="text-[10px] font-bold text-[#666666] uppercase block">Email Address</span>
                  <span className="font-mono text-[#1F1F1F]">{displayUser?.email || "N/A"}</span>
                </div>

                <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                  <span className="text-[10px] font-bold text-[#666666] uppercase block">Phone Number</span>
                  <span className="font-bold text-[#1F1F1F]">{displayUser?.phone || "Not provided"}</span>
                </div>

                <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                  <span className="text-[10px] font-bold text-[#666666] uppercase block">Department</span>
                  <span className="font-bold text-[#1F1F1F]">{displayUser?.department || "General"}</span>
                </div>

                <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                  <span className="text-[10px] font-bold text-[#666666] uppercase block">Job Title</span>
                  <span className="font-bold text-[#1F1F1F]">{displayUser?.job_title || "Team Member"}</span>
                </div>

                <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                  <span className="text-[10px] font-bold text-[#666666] uppercase block">Organization</span>
                  <span className="font-bold text-[#1F1F1F]">{displayUser?.org_name || "AgentGuard Enterprise"}</span>
                </div>
              </div>
            )}
          </div>

          {/* Email Verification Section */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
            <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Email Verification</h3>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-bold text-[#1F1F1F]">{displayUser?.email}</span>
                  {displayUser?.email_verified ? (
                    <span className="text-[11px] font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Verified
                    </span>
                  ) : (
                    <span className="text-[11px] font-bold px-2 py-0.5 bg-[#FFF4D9] text-[#F59A23] border border-[#F59A23]/30 rounded flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      Email Not Verified
                    </span>
                  )}
                </div>
                <p className="text-[12px] text-[#666666]">
                  Verified email address ensures secure account recovery and critical governance notifications.
                </p>
              </div>

              {!displayUser?.email_verified && (
                <button
                  type="button"
                  onClick={handleResendVerification}
                  disabled={verifyingEmail}
                  className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[12px] font-bold rounded-[6px] shrink-0 disabled:opacity-50"
                >
                  {verifyingEmail ? "Sending..." : "Resend Verification Email"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SECURITY SETTINGS */}
      {activeTab === "security" && (
        <div className="space-y-6">
          {/* Password Update Form */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
            <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Change Password</h3>
            <form onSubmit={handlePasswordUpdate} className="max-w-md space-y-4 text-[13px]">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-[#666666] uppercase">New Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter at least 6 characters"
                    required
                    className="w-full p-2.5 pr-10 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-[#666666] hover:text-[#1F1F1F]"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-[#666666] uppercase">Confirm New Password</label>
                <input
                  type={showPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  required
                  className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
                />
              </div>

              <button
                type="submit"
                disabled={passwordUpdating}
                className="px-4 py-2 bg-[#1F1F1F] hover:bg-[#333333] text-white text-[12px] font-bold rounded-[6px] disabled:opacity-50"
              >
                {passwordUpdating ? "Updating Password..." : "Update Password"}
              </button>
            </form>
          </div>

          {/* Active Sessions */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
            <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Active Authenticated Sessions</h3>
            <div className="divide-y divide-[#E8E8E4]">
              {sessions.map((s) => (
                <div key={s.id} className="py-3 flex items-center justify-between text-[12px]">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#1F1F1F]">{s.device}</span>
                      {s.is_current && (
                        <span className="text-[10px] font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] rounded">
                          Current Session
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-[#666666] font-mono">{s.ip_address}</span>
                  </div>

                  {!s.is_current && (
                    <button
                      type="button"
                      onClick={() => handleRevokeSession(s.id)}
                      className="px-3 py-1 bg-[#FFFFFF] border border-[#E8E8E4] text-[#E53935] text-[11px] font-bold rounded hover:bg-[#FDECEC]"
                    >
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: NOTIFICATIONS */}
      {activeTab === "notifications" && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-6">
          <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Notification Preferences</h3>
          
          <div className="space-y-4 max-w-2xl text-[13px]">
            {[
              { key: "securityAlerts", title: "Security Alerts", desc: "Real-time threat events, circuit breaker triggers, and SOC anomalies." },
              { key: "governanceAlerts", title: "Governance Policies", desc: "Policy violations, zero-trust enforcement actions, and refusal logs." },
              { key: "approvalNotifs", title: "Human Request Approvals", desc: "Managerial action requests requiring immediate sign-off." },
              { key: "systemNotifs", title: "System Updates & Announcements", desc: "Platform release notes and system maintenance windows." },
            ].map((item) => {
              const isChecked = (notifState as any)[item.key];
              return (
                <div key={item.key} className="flex items-center justify-between p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                  <div className="space-y-0.5">
                    <span className="font-bold text-[#1F1F1F] block">{item.title}</span>
                    <span className="text-[12px] text-[#666666]">{item.desc}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setNotifState({ ...notifState, [item.key]: !isChecked })}
                    className={`w-12 h-6 rounded-full transition-colors relative p-0.5 ${
                      isChecked ? "bg-[#2E9D50]" : "bg-[#CCCCCC]"
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                      isChecked ? "translate-x-6" : "translate-x-0"
                    }`} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 4: ORGANIZATION & ROLE OVERVIEW */}
      {activeTab === "organization" && (
        <div className="space-y-6">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
            <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Organization Membership</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Organization Name</span>
                <span className="text-[16px] font-bold text-[#1F1F1F]">{displayUser?.org_name || "AgentGuard Enterprise"}</span>
              </div>

              <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Your Assigned Role</span>
                <span className="text-[16px] font-bold text-[#8064C8]">{userRole}</span>
              </div>
            </div>

            {["ADMIN", "SUPER_ADMIN"].includes(userRole) && (
              <div className="pt-4 border-t border-[#E8E8E4] flex items-center justify-between">
                <div>
                  <h4 className="text-[13px] font-bold text-[#1F1F1F]">Organization Management</h4>
                  <p className="text-[12px] text-[#666666]">Manage workspace members, assign 9-tier roles & scoping.</p>
                </div>
                <Link
                  href="/iam"
                  className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[12px] font-bold rounded-[6px]"
                >
                  Manage IAM Users
                </Link>
              </div>
            )}
          </div>

          {/* SUPER ADMIN SPECIAL PLATFORM PERMISSIONS SECTION */}
          {userRole === "SUPER_ADMIN" && (
            <div className="bg-[#FFFFFF] border border-[#8064C8]/40 rounded-[12px] p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-[#E8E8E4] pb-3">
                <Globe className="w-5 h-5 text-[#8064C8]" />
                <h3 className="text-[16px] font-bold text-[#1F1F1F]">SUPER_ADMIN Platform Permissions</h3>
              </div>
              <p className="text-[12px] text-[#666666]">
                You possess full platform-wide authorization across all organizations and global control plane resources.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-[12px] font-bold">
                {[
                  "✓ Organizations",
                  "✓ Users",
                  "✓ Roles",
                  "✓ Policies",
                  "✓ Agents",
                  "✓ Security",
                  "✓ Audit",
                  "✓ System",
                  "✓ Platform Settings",
                ].map((perm) => (
                  <div key={perm} className="p-2.5 bg-[#F1EDFA] border border-[#8064C8]/30 rounded text-[#8064C8]">
                    {perm}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
