"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/lib/useAuth";
import { fetchApi } from "@/lib/api";
import { Bell, User, Settings, LogOut, ShieldCheck, ChevronDown, Building, CheckCircle } from "lucide-react";

export default function DashboardHeader() {
  const { user, logout } = useAuth();
  const userRole = user?.role || "USER";

  const [orgBranding, setOrgBranding] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [brandData, notifData] = await Promise.all([
          fetchApi("/organization/branding").catch(() => null),
          fetchApi("/notifications").catch(() => []),
        ]);
        if (brandData) setOrgBranding(brandData);
        if (notifData) setNotifications(notifData);
      } catch (err) {
        console.error("Header load error:", err);
      }
    }
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

  const userInitials = getInitials(user?.full_name, user?.email);
  const tenantLogo = orgBranding?.logo_url;
  const tenantName = orgBranding?.display_name || orgBranding?.name || user?.org_name || "AgentGuard Enterprise";
  const tenantInitials = orgBranding?.initials || getInitials(tenantName, undefined);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <header className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
      {/* 1. Brand Hierarchy Header */}
      <div className="flex items-center gap-4">
        {/* AGENTGUARD Platform Logo */}
        <div className="w-10 h-10 rounded-[8px] bg-[#FCFCFA] border border-[#E8E8E4] p-1 flex items-center justify-center shrink-0 shadow-sm">
          <Image src="/logo.png" alt="AGENTGUARD Logo" width={32} height={32} className="object-contain" />
        </div>

        <div className="h-8 w-[1px] bg-[#E8E8E4] hidden md:block" />

        {/* Customer Organization Tenant Identity */}
        <div className="flex items-center gap-3">
          {tenantLogo ? (
            <img
              src={tenantLogo}
              alt={`${tenantName} Logo`}
              className="w-9 h-9 rounded-[8px] object-cover border border-[#8064C8] shadow-sm shrink-0"
            />
          ) : (
            <div className="w-9 h-9 rounded-[8px] bg-[#8064C8] text-white flex items-center justify-center text-[13px] font-bold shrink-0 shadow-sm">
              {tenantInitials}
            </div>
          )}

          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[16px] font-bold text-[#1F1F1F] leading-none">{tenantName}</h2>
              <span className="text-[9px] font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/20 rounded-full uppercase">
                Isolated Tenant
              </span>
            </div>
            <p className="text-[10px] font-bold text-[#666666] tracking-wide mt-1">
              licensed by <span className="text-[#2E9D50] font-bold">AGENTGUARD</span>
            </p>
          </div>
        </div>
      </div>

      {/* 2. Right Side Workspace Actions */}
      <div className="flex items-center gap-4 shrink-0">
        {/* Notifications Icon Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="w-9 h-9 rounded-[8px] bg-[#FCFCFA] border border-[#E8E8E4] flex items-center justify-center hover:bg-[#F0F0ED] transition-colors relative"
          >
            <Bell className="w-4 h-4 text-[#1F1F1F]" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#E53935] text-white text-[9px] font-bold flex items-center justify-center border border-white">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] shadow-xl p-3 z-30 space-y-2 text-[12px]">
              <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-2 font-bold text-[#1F1F1F]">
                <span>Notifications & Alerts</span>
                <span className="text-[10px] text-[#2E9D50] uppercase font-mono">{unreadCount} unread</span>
              </div>
              {notifications.length === 0 ? (
                <p className="text-[#666666] text-[11px] py-2 text-center">No active notifications</p>
              ) : (
                <div className="max-h-60 overflow-y-auto space-y-2">
                  {notifications.slice(0, 5).map((n, idx) => (
                    <div key={idx} className="p-2 bg-[#FCFCFA] rounded-[6px] border border-[#E8E8E4] space-y-0.5">
                      <span className="font-bold text-[#1F1F1F] block">{n.title}</span>
                      <p className="text-[11px] text-[#666666]">{n.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Role Badge */}
        <span className="text-[11px] font-bold px-2.5 py-1 bg-[#F1EDFA] text-[#8064C8] border border-[#8064C8]/30 rounded-full uppercase font-mono">
          {userRole}
        </span>

        {/* User Profile Menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-1.5 rounded-[8px] bg-[#FCFCFA] border border-[#E8E8E4] hover:bg-[#F0F0ED] transition-colors"
          >
            <div className="w-7 h-7 rounded-[6px] bg-[#1F1F1F] text-white flex items-center justify-center text-[11px] font-bold border border-[#2E9D50]">
              {userInitials}
            </div>
            <span className="text-[12px] font-bold text-[#1F1F1F] hidden md:block max-w-[100px] truncate">
              {user?.full_name?.split(" ")[0] || "User"}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-[#666666]" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] shadow-xl p-2 z-30 space-y-1 text-[12px] font-bold">
              <div className="px-3 py-2 border-b border-[#E8E8E4]">
                <span className="text-[#1F1F1F] block truncate">{user?.full_name || "User"}</span>
                <span className="text-[10px] text-[#666666] block font-mono truncate">{user?.email}</span>
              </div>

              <Link
                href="/profile"
                className="flex items-center gap-2 px-3 py-2 hover:bg-[#EAF7EE] text-[#1F1F1F] hover:text-[#237A3C] rounded-[6px] transition-colors"
              >
                <User className="w-4 h-4 text-[#2E9D50]" />
                <span>My Profile</span>
              </Link>

              <Link
                href="/settings"
                className="flex items-center gap-2 px-3 py-2 hover:bg-[#EAF7EE] text-[#1F1F1F] hover:text-[#237A3C] rounded-[6px] transition-colors"
              >
                <Settings className="w-4 h-4 text-[#2E9D50]" />
                <span>Account Settings</span>
              </Link>

              <button
                onClick={() => logout()}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[#FDECEC] text-[#E53935] rounded-[6px] transition-colors text-left"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
