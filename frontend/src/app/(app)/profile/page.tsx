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
  Globe,
  FileSearch,
  Mail,
  Smartphone
} from "lucide-react";

export default function ProfilePage() {
  const { user, refreshProfile, logout } = useAuth();
  const [profileData, setProfileData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "security" | "sessions" | "activity">("overview");
  const [loading, setLoading] = useState(true);

  // Profile Edit State
  const [isEditing, setIsEditing] = useState(false);
  const [editFullName, setEditFullName] = useState("");
  const [editDepartment, setEditDepartment] = useState("");
  const [editJobTitle, setEditJobTitle] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [updating, setUpdating] = useState(false);
  const [notice, setNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Security / Password State
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [passwordUpdating, setPasswordUpdating] = useState(false);

  // Verification & Sessions
  const [verifyingEmail, setVerifyingEmail] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);

  const loadProfileDetails = async () => {
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
    } catch (err: any) {
      console.error("Profile load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfileDetails();
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
      setNotice({ type: "success", message: "Personal profile information successfully updated!" });
      setIsEditing(false);
      await refreshProfile();
      await loadProfileDetails();
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
      await loadProfileDetails();
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
        <p className="text-[13px]">Loading authenticated user profile from Supabase...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header Banner & Avatar */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          {/* Dynamic Avatar Initials Badge */}
          <div className="w-20 h-20 rounded-[16px] bg-[#1F1F1F] text-white flex items-center justify-center text-[28px] font-bold shadow-lg border-2 border-[#2E9D50] shrink-0">
            {initials}
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-[24px] font-bold text-[#1F1F1F]">{displayUser?.full_name || "Enterprise User"}</h1>
              <span className="text-[11px] font-bold px-3 py-0.5 bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/30 rounded-full uppercase">
                {userRole}
              </span>
            </div>
            <p className="text-[13px] text-[#666666] font-mono">{displayUser?.email}</p>
            <div className="flex items-center gap-4 pt-1 text-[12px] text-[#666666]">
              <span className="font-bold text-[#1F1F1F]">
                {userRole === "SUPER_ADMIN" ? "Platform Owner (Global Scope)" : (displayUser?.org_name || "AgentGuard Enterprise")}
              </span>
              <span>•</span>
              <span className="font-mono text-[11px]">
                {userRole === "SUPER_ADMIN" ? "Access: ALL ORGANIZATIONS" : `ID: ${displayUser?.id ? String(displayUser.id).substring(0, 8) + "..." : "usr_id"}`}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/settings"
            className="px-4 py-2 bg-[#FCFCFA] border border-[#E8E8E4] text-[#1F1F1F] text-[13px] font-bold rounded-[8px] hover:bg-[#F0F0ED] transition-colors"
          >
            Account Settings
          </Link>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[13px] font-bold rounded-[8px] flex items-center gap-2 transition-colors"
            >
              <Edit3 className="w-4 h-4" />
              <span>Edit Profile</span>
            </button>
          )}
        </div>
      </div>

      {/* Notice Alert Banner */}
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

      {/* Profile Page Navigation Tabs */}
      <div className="flex border-b border-[#E8E8E4] gap-6 text-[13px] font-bold">
        {[
          { id: "overview", label: "OVERVIEW", icon: User },
          { id: "security", label: "SECURITY & CREDENTIALS", icon: Shield },
          { id: "sessions", label: "ACTIVE SESSIONS", icon: Clock },
          { id: "activity", label: "ACCOUNT ACTIVITY", icon: Activity },
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

      {/* TAB 1: OVERVIEW & PERSONAL INFO */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Personal Info Box */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-6">
            <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">Personal Information</h3>
              <span className="text-[11px] font-bold text-[#666666]">Real Supabase Data</span>
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

          {/* Account Security Metadata */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
            <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Account Security & Verification</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-[13px]">
              <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Email Verification</span>
                {displayUser?.email_verified ? (
                  <span className="text-[12px] font-bold text-[#237A3C] flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Verified
                  </span>
                ) : (
                  <span className="text-[12px] font-bold text-[#F59A23] flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    Not Verified
                  </span>
                )}
              </div>

              <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Account Status</span>
                <span className="text-[12px] font-bold text-[#237A3C] uppercase">{displayUser?.status || "ACTIVE"}</span>
              </div>

              <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Member Since</span>
                <span className="text-[12px] font-bold text-[#1F1F1F]">
                  {displayUser?.created_at ? new Date(displayUser.created_at).toLocaleDateString() : "31 Aug 2026"}
                </span>
              </div>

              <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Last Login</span>
                <span className="text-[12px] font-bold text-[#1F1F1F]">
                  {displayUser?.last_login_at ? new Date(displayUser.last_login_at).toLocaleString() : "Just now"}
                </span>
              </div>
            </div>
          </div>

          {/* Role & Access Box */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">Role & Access Authority</h3>
              <span className="text-[11px] font-bold text-[#8064C8] uppercase bg-[#F1EDFA] px-2.5 py-0.5 rounded border border-[#8064C8]/30">
                Level {displayUser?.role_level || 1} / 9
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
              <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Assigned Role</span>
                <span className="text-[18px] font-bold text-[#8064C8]">{userRole}</span>
              </div>

              <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                <span className="text-[10px] font-bold text-[#666666] uppercase block">Role Description</span>
                <span className="text-[12px] text-[#666666]">{displayUser?.role_description || "Authenticated Human User"}</span>
              </div>
            </div>

            {/* SUPER ADMIN platform permissions card */}
            {userRole === "SUPER_ADMIN" && (
              <div className="p-4 bg-[#F1EDFA] border border-[#8064C8]/30 rounded-[8px] space-y-2">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-[#8064C8]" />
                  <span className="text-[13px] font-bold text-[#8064C8]">SUPER_ADMIN Platform Authority</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] font-mono font-bold text-[#8064C8]">
                  <span>✓ Organizations</span>
                  <span>✓ Users</span>
                  <span>✓ Roles</span>
                  <span>✓ Policies</span>
                  <span>✓ Agents</span>
                  <span>✓ Security</span>
                  <span>✓ Audit</span>
                  <span>✓ System</span>
                  <span>✓ Platform Settings</span>
                </div>
              </div>
            )}

            {/* ADMIN organization access card */}
            {userRole === "ADMIN" && (
              <div className="p-4 bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-[8px] space-y-2">
                <div className="flex items-center gap-2">
                  <Building className="w-4 h-4 text-[#2E9D50]" />
                  <span className="text-[13px] font-bold text-[#237A3C]">ADMIN Organization Authority</span>
                </div>
                <p className="text-[12px] text-[#237A3C]">
                  Full administrative control within your organization workspace ({displayUser?.org_name || "AgentGuard Enterprise"}).
                </p>
              </div>
            )}

            <div className="space-y-2 pt-2">
              <span className="text-[12px] font-bold text-[#1F1F1F]">Effective Permissions Matrix</span>
              <div className="flex flex-wrap gap-2">
                {(displayUser?.effective_permissions || ["dashboard:read", "profile:read"]).map((p: string) => (
                  <span key={p} className="px-2.5 py-1 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] text-[11px] font-mono font-bold text-[#444444]">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SECURITY & CREDENTIALS */}
      {activeTab === "security" && (
        <div className="space-y-6">
          {/* Password Update Form */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
            <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Update Password</h3>
            <p className="text-[12px] text-[#666666]">
              Password authentication credentials are handled securely via Supabase Auth.
            </p>

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
                {passwordUpdating ? "Updating..." : "Update Password"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 3: ACTIVE SESSIONS */}
      {activeTab === "sessions" && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
          <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Active Authenticated Sessions</h3>
          <div className="divide-y divide-[#E8E8E4]">
            {sessions.length === 0 ? (
              <p className="py-4 text-[12px] text-[#666666]">Active session data currently managed by Supabase Auth Token.</p>
            ) : (
              sessions.map((s) => (
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
                      Revoke Session
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 4: ACCOUNT ACTIVITY LOGS */}
      {activeTab === "activity" && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-4">
          <h3 className="text-[16px] font-bold text-[#1F1F1F] border-b border-[#E8E8E4] pb-3">Personal Account Activity Log</h3>
          {activities.length === 0 ? (
            <p className="text-[12px] text-[#666666] py-4">No recent security or profile event activity logged.</p>
          ) : (
            <div className="divide-y divide-[#E8E8E4]">
              {activities.map((act) => (
                <div key={act.id} className="py-3 flex items-center justify-between text-[12px]">
                  <div className="space-y-0.5">
                    <span className="font-bold text-[#1F1F1F] block">{act.action || act.event_type}</span>
                    <span className="text-[11px] text-[#666666] font-mono">{act.resource || "Profile Subsystem"}</span>
                  </div>
                  <span className="text-[11px] text-[#666666]">
                    {act.timestamp ? new Date(act.timestamp).toLocaleString() : "Recently"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
