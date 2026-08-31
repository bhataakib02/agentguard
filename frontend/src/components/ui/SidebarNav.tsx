"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { hasRoutePermission } from "@/lib/permissions";
import { fetchApi } from "@/lib/api";
import {
  LayoutDashboard,
  Bot,
  ShieldCheck,
  Zap,
  Scale,
  Shield,
  Activity,
  Flame,
  UserCheck,
  FileSearch,
  Brain,
  Radio,
  LogOut,
  Users,
  DollarSign,
  Cpu,
  GitFork,
  Building,
  Globe,
  Lock,
  User,
  Settings,
  UserCircle,
  ChevronDown
} from "lucide-react";

export default function SidebarNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const userRole = user?.role || "USER";

  const [orgBranding, setOrgBranding] = useState<any>(null);
  const [orgList, setOrgList] = useState<any[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("ALL");

  useEffect(() => {
    async function loadBranding() {
      try {
        const data = await fetchApi("/organization/branding").catch(() => null);
        setOrgBranding(data);

        if (userRole === "SUPER_ADMIN") {
          const orgs = await fetchApi("/platform/organizations").catch(() => []);
          setOrgList(orgs || []);
        }
      } catch (err) {
        console.error("Branding load error:", err);
      }
    }
    loadBranding();
  }, [userRole]);

  const getInitials = (name?: string, email?: string) => {
    if (name && name.trim().length > 0) {
      const parts = name.trim().split(" ");
      if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      return parts[0].substring(0, 2).toUpperCase();
    }
    if (email) return email.substring(0, 2).toUpperCase();
    return "AG";
  };

  const initials = getInitials(user?.full_name, user?.email);
  const orgInitials = orgBranding?.initials || getInitials(user?.org_name, undefined);

  const allNavItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "User Profile", href: "/profile", icon: UserCircle },
    { label: "Account Settings", href: "/settings", icon: Settings },
    { label: "AI Directory", href: "/agents", icon: Bot },
    { label: "Permission Matrix", href: "/permissions", icon: ShieldCheck },
    { label: "Capability Tokens", href: "/capabilities", icon: Zap },
    { label: "Governance Policies", href: "/policies", icon: Scale },
    { label: "Decision Black Box", href: "/decisions", icon: Shield },
    { label: "Risk Scoring", href: "/risk", icon: Activity },
    { label: "Circuit Breaker", href: "/runtime", icon: Flame },
    { label: "Human Approvals", href: "/approvals", icon: UserCheck },
    { label: "Audit Logs", href: "/audit", icon: FileSearch },
    { label: "Causal Provenance", href: "/provenance", icon: GitFork },
    { label: "Red-Team Lab", href: "/red-team", icon: Flame },
    { label: "Digital Twin", href: "/digital-twin", icon: Cpu },
    { label: "AI Assistant", href: "/assistant", icon: Brain },
    { label: "Live Activity", href: "/activity", icon: Radio },
    { label: "IAM Users", href: "/iam", icon: Users },
    { label: "Organization", href: "/organization", icon: Building },
    { label: "Report Center", href: "/reports", icon: FileSearch },
    { label: "Economics", href: "/economics", icon: DollarSign },
    { label: "Platform Admin", href: "/platform", icon: Globe },
  ];

  const visibleItems = allNavItems.filter((item) => hasRoutePermission(userRole, item.href));

  return (
    <aside className="w-64 bg-[#FFFFFF] border-r border-[#E8E8E4] flex flex-col h-screen fixed left-0 top-0 z-20">
      {/* 1. AGENTGUARD Platform Brand Header */}
      <div className="p-4 border-b border-[#E8E8E4] flex items-center gap-3">
        <div className="w-9 h-9 rounded-[8px] bg-[#FCFCFA] border border-[#E8E8E4] p-1 flex items-center justify-center shrink-0 shadow-sm">
          <Image src="/logo.png" alt="AgentGuard Platform Logo" width={28} height={28} className="object-contain" />
        </div>
        <div className="overflow-hidden">
          <h1 className="text-[17px] font-bold text-[#1F1F1F] leading-none">AGENTGUARD</h1>
          <p className="text-[9px] font-bold text-[#2E9D50] uppercase tracking-wider mt-1">Control Plane</p>
        </div>
      </div>

      {/* 2. Customer Organization Dual Branding Banner */}
      <div className="px-4 py-3 border-b border-[#E8E8E4] bg-[#FCFCFA] space-y-1.5">
        <div className="text-[10px] font-bold text-[#666666] uppercase tracking-wider">
          {userRole === "SUPER_ADMIN" ? "Super Admin Context" : "Tenant Organization Workspace"}
        </div>

        {userRole === "SUPER_ADMIN" ? (
          <div className="relative">
            <select
              value={selectedOrgId}
              onChange={(e) => setSelectedOrgId(e.target.value)}
              className="w-full text-[12px] font-bold bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] px-2 py-1 text-[#1F1F1F] outline-none cursor-pointer"
            >
              <option value="ALL">🌐 All Organizations (Global)</option>
              {orgList.map((o) => (
                <option key={o.id} value={o.id}>
                  🏢 {o.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="flex items-center gap-2.5">
            {orgBranding?.logo_url ? (
              <img
                src={orgBranding.logo_url}
                alt={`${orgBranding.name} Logo`}
                className="w-7 h-7 rounded-[6px] object-cover border border-[#E8E8E4] shrink-0"
              />
            ) : (
              <div className="w-7 h-7 rounded-[6px] bg-[#8064C8] text-white flex items-center justify-center text-[11px] font-bold shrink-0">
                {orgInitials}
              </div>
            )}
            <div className="overflow-hidden">
              <span className="font-bold text-[#1F1F1F] text-[13px] block truncate">
                {orgBranding?.display_name || user?.org_name || "AgentGuard Enterprise"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href === "/dashboard" && pathname === "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-[8px] text-[13px] font-bold transition-colors ${
                isActive
                  ? "bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30"
                  : "text-[#1F1F1F] hover:bg-[#FCFCFA] hover:text-[#2E9D50]"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-[#2E9D50]" : "text-[#666666]"}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User Profile Footer Card & Quick Action Buttons */}
      <div className="p-4 border-t border-[#E8E8E4] bg-[#FCFCFA] space-y-3">
        {/* Clickable Profile Card -> Navigates to /profile */}
        <Link
          href="/profile"
          className="flex items-center gap-3 p-2 rounded-[8px] hover:bg-[#FFFFFF] border border-transparent hover:border-[#E8E8E4] transition-all group"
        >
          <div className="w-9 h-9 rounded-[8px] bg-[#1F1F1F] text-white flex items-center justify-center text-[13px] font-bold border border-[#2E9D50] shrink-0 group-hover:scale-105 transition-transform">
            {initials}
          </div>
          <div className="text-[12px] space-y-0.5 overflow-hidden">
            <span className="font-bold text-[#1F1F1F] block truncate group-hover:text-[#2E9D50]">
              {user?.full_name || "Enterprise User"}
            </span>
            <span className="text-[11px] text-[#666666] block truncate font-mono">{user?.email || "user@enterprise.ai"}</span>
          </div>
        </Link>

        <div className="flex items-center justify-between pt-1 text-[10px]">
          <span className="font-bold text-[#8064C8] uppercase bg-[#F1EDFA] px-2 py-0.5 rounded border border-[#8064C8]/20">
            {userRole}
          </span>
          <span className="text-[#666666] font-mono truncate max-w-[110px]">
            {userRole === "SUPER_ADMIN" ? "Platform Scope" : (user?.org_name || "AgentGuard")}
          </span>
        </div>

        {/* Quick Links for Profile & Settings */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <Link
            href="/profile"
            className={`flex items-center justify-center gap-1.5 py-1.5 rounded-[6px] text-[11px] font-bold transition-colors border ${
              pathname === "/profile"
                ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/40"
                : "bg-[#FFFFFF] text-[#1F1F1F] border-[#E8E8E4] hover:bg-[#FCFCFA]"
            }`}
          >
            <User className="w-3.5 h-3.5 text-[#2E9D50]" />
            <span>Profile</span>
          </Link>

          <Link
            href="/settings"
            className={`flex items-center justify-center gap-1.5 py-1.5 rounded-[6px] text-[11px] font-bold transition-colors border ${
              pathname === "/settings"
                ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/40"
                : "bg-[#FFFFFF] text-[#1F1F1F] border-[#E8E8E4] hover:bg-[#FCFCFA]"
            }`}
          >
            <Settings className="w-3.5 h-3.5 text-[#2E9D50]" />
            <span>Settings</span>
          </Link>
        </div>

        <button
          onClick={() => logout()}
          className="w-full flex items-center justify-center gap-2 py-1.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] text-[12px] font-bold text-[#E53935] hover:bg-[#FDECEC] transition-colors mt-1"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
