"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { fetchApi } from "@/lib/api";
import {
  LayoutDashboard,
  Building,
  Users,
  Bot,
  CreditCard,
  DollarSign,
  Activity,
  ShieldAlert,
  FileSearch,
  FileText,
  Cpu,
  Server,
  Settings,
  User,
  Shield,
  LogOut,
  Search,
  Bell,
  HelpCircle,
  Menu,
  X,
  RefreshCw,
  Globe
} from "lucide-react";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, loading } = useAuth();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.push("/login");
      } else if (user.role !== "SUPER_ADMIN") {
        router.push("/403");
      }
    }
  }, [user, loading, router]);

  useEffect(() => {
    async function loadNotifs() {
      try {
        const notifs = await fetchApi("/notifications").catch(() => []);
        setNotifications(notifs || []);
      } catch (err) {}
    }
    if (user?.role === "SUPER_ADMIN") loadNotifs();
  }, [user]);

  const handleSearch = async (val: string) => {
    setSearchQuery(val);
    if (val.trim().length < 2) {
      setSearchResults([]);
      setShowSearchDropdown(false);
      return;
    }
    setIsSearching(true);
    setShowSearchDropdown(true);
    try {
      const res = await fetchApi(`/platform/search?q=${encodeURIComponent(val.trim())}`);
      setSearchResults(res || []);
    } catch (e) {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const navPlatform = [
    { label: "Overview", href: "/platform", icon: LayoutDashboard },
    { label: "Organizations", href: "/platform/organizations", icon: Building },
    { label: "Users", href: "/platform/users", icon: Users },
    { label: "AI Agents", href: "/platform/agents", icon: Bot },
    { label: "Licenses", href: "/platform/licenses", icon: CreditCard },
    { label: "Billing", href: "/platform/billing", icon: DollarSign },
    { label: "Usage & Analytics", href: "/platform/analytics", icon: Activity },
    { label: "Security", href: "/platform/security", icon: ShieldAlert },
    { label: "Audit Logs", href: "/platform/audit", icon: FileSearch },
    { label: "Reports", href: "/platform/reports", icon: FileText },
    { label: "API / Integrations", href: "/platform/integrations", icon: Cpu },
    { label: "System Health", href: "/platform/system-health", icon: Server },
    { label: "Platform Settings", href: "/platform/settings", icon: Settings },
  ];

  const navTenant = [
    { label: "Organization Directory", href: "/platform/organizations", icon: Building },
    { label: "Organization Activity", href: "/platform/audit", icon: Activity },
    { label: "Organization Limits", href: "/platform/licenses", icon: CreditCard },
    { label: "Organization Licenses", href: "/platform/licenses", icon: Shield },
  ];

  const navAccount = [
    { label: "My Profile", href: "/platform/profile", icon: User },
    { label: "My Security", href: "/platform/security", icon: Shield },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0D14] text-white flex items-center justify-center">
        <div className="flex items-center gap-3">
          <RefreshCw className="w-6 h-6 animate-spin text-[#2E9D50]" />
          <span className="font-bold text-[14px]">Loading AGENTGUARD Platform Control Center...</span>
        </div>
      </div>
    );
  }

  if (!user || user.role !== "SUPER_ADMIN") {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#0A0D14] text-[#E1E7F0] flex flex-col justify-between font-sans selection:bg-[#2E9D50] selection:text-white">
      <div className="flex flex-col lg:flex-row flex-1">
        {/* Mobile Top Header */}
        <div className="lg:hidden sticky top-0 z-40 bg-[#0F131D] border-b border-[#1E2638] px-4 py-3 flex items-center justify-between shadow-md">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-[#E1E7F0] hover:bg-[#1E2638] rounded-[8px]"
            >
              {mobileMenuOpen ? <X className="w-5 h-5 text-[#E53935]" /> : <Menu className="w-5 h-5" />}
            </button>
            <div className="flex items-center gap-2">
              <Image src="/logo.png" alt="AGENTGUARD Logo" width={24} height={24} className="object-contain" />
              <span className="font-bold text-[15px] text-white tracking-wide">AGENTGUARD PLATFORM</span>
            </div>
          </div>

          <span className="text-[9px] font-bold px-2 py-0.5 bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 rounded uppercase">
            GLOBAL PLATFORM
          </span>
        </div>

        {/* Backdrop for Mobile Drawer */}
        {mobileMenuOpen && (
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-black/70 backdrop-blur-xs z-40 lg:hidden"
          />
        )}

        {/* Dedicated Super Admin Dark Sidebar */}
        <aside
          className={`w-64 bg-[#0F131D] border-r border-[#1E2638] flex flex-col h-screen fixed left-0 top-0 z-50 transition-transform duration-300 lg:translate-x-0 ${
            mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          {/* Sidebar Header */}
          <div className="p-4 border-b border-[#1E2638] flex items-center gap-3">
            <div className="w-9 h-9 rounded-[8px] bg-[#161C2A] border border-[#232F48] p-1 flex items-center justify-center shrink-0 shadow-inner">
              <Image src="/logo.png" alt="AGENTGUARD Brand Logo" width={28} height={28} className="object-contain" />
            </div>
            <div className="overflow-hidden">
              <h1 className="text-[14px] font-bold text-white leading-none tracking-tight">AGENTGUARD</h1>
              <p className="text-[9px] font-bold text-[#2E9D50] uppercase tracking-wider mt-1">PLATFORM CONTROL CENTER</p>
            </div>
          </div>

          {/* Sidebar Navigation */}
          <div className="flex-1 overflow-y-auto p-3 space-y-5 text-[12px] scrollbar-thin scrollbar-thumb-[#1E2638]">
            {/* PLATFORM */}
            <div className="space-y-1">
              <div className="px-3 py-1 text-[10px] font-bold text-[#2E9D50] uppercase tracking-wider font-mono">
                PLATFORM
              </div>
              {navPlatform.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || (item.href === "/platform" && pathname === "/platform");
                return (
                  <Link
                    key={item.href + item.label}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-[8px] font-bold transition-all ${
                      isActive
                        ? "bg-[#173B25] text-white border border-[#2E9D50]/50 shadow-sm"
                        : "text-[#94A3B8] hover:bg-[#161C2A] hover:text-white"
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? "text-[#2E9D50]" : "text-[#64748B]"}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>

            {/* TENANT MANAGEMENT */}
            <div className="space-y-1">
              <div className="px-3 py-1 text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">
                TENANT MANAGEMENT
              </div>
              {navTenant.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href + item.label}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-[8px] font-bold transition-all ${
                      isActive
                        ? "bg-[#173B25] text-white border border-[#2E9D50]/50"
                        : "text-[#94A3B8] hover:bg-[#161C2A] hover:text-white"
                    }`}
                  >
                    <Icon className="w-4 h-4 text-[#64748B]" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>

            {/* ACCOUNT */}
            <div className="space-y-1">
              <div className="px-3 py-1 text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">
                ACCOUNT
              </div>
              {navAccount.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href + item.label}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-[8px] font-bold transition-all ${
                      isActive
                        ? "bg-[#173B25] text-white border border-[#2E9D50]/50"
                        : "text-[#94A3B8] hover:bg-[#161C2A] hover:text-white"
                    }`}
                  >
                    <Icon className="w-4 h-4 text-[#64748B]" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Sidebar Footer User Card */}
          <div className="p-4 border-t border-[#1E2638] bg-[#0A0D14] space-y-3">
            <div className="p-2.5 rounded-[10px] bg-[#121722] border border-[#1E2638] space-y-2">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-[8px] bg-[#173B25] border border-[#2E9D50] text-[#2E9D50] font-bold flex items-center justify-center text-[12px] shadow-sm shrink-0">
                  SA
                </div>
                <div className="overflow-hidden">
                  <span className="font-bold text-white text-[12px] block truncate">SUPER_ADMIN</span>
                  <span className="text-[10px] text-[#64748B] block truncate font-mono">Platform Administrator</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-[9px] pt-1 border-t border-[#1E2638]">
                <span className="font-bold text-[#2E9D50] bg-[#173B25] px-2 py-0.5 rounded border border-[#2E9D50]/30 font-mono flex items-center gap-1">
                  <Globe className="w-3 h-3" /> Global Access
                </span>
                <button
                  onClick={() => logout()}
                  className="text-[#E53935] hover:underline font-bold flex items-center gap-1"
                >
                  <LogOut className="w-3 h-3" /> Logout
                </button>
              </div>
            </div>

            <div className="text-[9px] text-[#64748B] font-mono space-y-0.5 px-1">
              <div>Version 2.0.0</div>
              <div>© 2025 AgentGuard Inc.</div>
            </div>
          </div>
        </aside>

        {/* Main Section */}
        <main className="flex-1 lg:ml-64 flex flex-col overflow-x-hidden bg-[#F4F6F8]">
          {/* Top Header Bar */}
          <header className="bg-[#0F131D] border-b border-[#1E2638] px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 sticky top-0 z-30 shadow-sm">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-[20px] font-bold text-white tracking-tight">Platform Overview</h1>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
                  GLOBAL PLATFORM
                </span>
              </div>
              <p className="text-[12px] text-[#64748B] mt-0.5">Global platform administration and monitoring</p>
            </div>


            <div className="flex items-center gap-4 w-full md:w-auto justify-between md:justify-end">
              {/* Search input with ⌘K badge */}
              <div className="relative flex-1 md:w-80">
                <div className="relative">
                  <Search className="w-4 h-4 text-[#64748B] absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search organizations, users, agents, licenses, audit logs..."
                    value={searchQuery}
                    onChange={(e) => handleSearch(e.target.value)}
                    onFocus={() => searchQuery.length >= 2 && setShowSearchDropdown(true)}
                    className="w-full pl-9 pr-10 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[12px] text-white placeholder-[#64748B] outline-none focus:border-[#2E9D50] transition-colors"
                  />
                  <span className="absolute right-2.5 top-2 bg-[#1E2638] text-[#94A3B8] text-[9px] font-mono px-1.5 py-0.5 rounded border border-[#232F48]">
                    ⌘K
                  </span>
                </div>

                {/* Instant Search Results Dropdown */}
                {showSearchDropdown && (
                  <div className="absolute right-0 left-0 mt-2 bg-[#121722] border border-[#1E2638] rounded-[10px] shadow-2xl p-2 z-50 space-y-1 text-[12px] max-h-80 overflow-y-auto">
                    <div className="px-3 py-1.5 border-b border-[#1E2638] font-bold text-[#64748B] text-[10px] uppercase flex justify-between">
                      <span>Search Results</span>
                      <button onClick={() => setShowSearchDropdown(false)} className="hover:text-white">Close</button>
                    </div>

                    {isSearching ? (
                      <div className="p-4 text-center text-[#64748B] text-[11px]">Searching database...</div>
                    ) : searchResults.length === 0 ? (
                      <div className="p-4 text-center text-[#64748B] text-[11px]">No results found matching "{searchQuery}"</div>
                    ) : (
                      searchResults.map((item, idx) => (
                        <Link
                          key={idx}
                          href={item.url}
                          onClick={() => setShowSearchDropdown(false)}
                          className="flex items-center justify-between p-2 hover:bg-[#1A2234] rounded-[6px] transition-colors group"
                        >
                          <div>
                            <div className="font-bold text-white group-hover:text-[#2E9D50]">{item.title}</div>
                            <div className="text-[10px] text-[#64748B] font-mono">{item.subtitle}</div>
                          </div>
                          <span className="text-[9px] font-bold uppercase bg-[#173B25] text-[#2E9D50] px-2 py-0.5 rounded border border-[#2E9D50]/30">
                            {item.type}
                          </span>
                        </Link>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Notification icon */}
              <div className="relative">
                <button
                  onClick={() => setShowNotifDropdown(!showNotifDropdown)}
                  className="w-9 h-9 rounded-[8px] bg-[#161C2A] border border-[#232F48] flex items-center justify-center hover:bg-[#1E2638] transition-colors relative"
                >
                  <Bell className="w-4 h-4 text-[#94A3B8]" />
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#E53935] text-white text-[9px] font-bold flex items-center justify-center border border-[#0F131D]">
                    12
                  </span>
                </button>

                {showNotifDropdown && (
                  <div className="absolute right-0 mt-2 w-72 bg-[#121722] border border-[#1E2638] rounded-[10px] shadow-2xl p-3 z-50 space-y-2 text-[12px]">
                    <div className="flex items-center justify-between border-b border-[#1E2638] pb-2 font-bold text-white">
                      <span>Platform Alerts</span>
                      <span className="text-[10px] text-[#2E9D50] font-mono uppercase">Global Scope</span>
                    </div>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      <div className="p-2 bg-[#1A2234] rounded-[6px] border border-[#232F48] space-y-0.5">
                        <span className="font-bold text-white block">License Expiring Soon</span>
                        <p className="text-[11px] text-[#94A3B8]">UrbanGrid Logistics license expires in 24 days.</p>
                      </div>
                      <div className="p-2 bg-[#1A2234] rounded-[6px] border border-[#232F48] space-y-0.5">
                        <span className="font-bold text-white block">Security Incident Alert</span>
                        <p className="text-[11px] text-[#94A3B8]">Critical risk flag evaluated for MedCore Health Systems.</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Help icon */}
              <button className="w-9 h-9 rounded-[8px] bg-[#161C2A] border border-[#232F48] hidden sm:flex items-center justify-center hover:bg-[#1E2638] transition-colors">
                <HelpCircle className="w-4 h-4 text-[#94A3B8]" />
              </button>

              {/* Profile Avatar */}
              <div className="relative">
                <button
                  onClick={() => setShowUserDropdown(!showUserDropdown)}
                  className="flex items-center gap-2.5 p-1.5 rounded-[8px] bg-[#161C2A] border border-[#232F48] hover:bg-[#1E2638] transition-colors"
                >
                  <div className="w-7 h-7 rounded-[6px] bg-[#173B25] text-[#2E9D50] border border-[#2E9D50] font-bold flex items-center justify-center text-[11px]">
                    SA
                  </div>
                  <div className="text-left hidden sm:block">
                    <span className="text-[11px] font-bold text-white block leading-none">SUPER_ADMIN</span>
                    <span className="text-[9px] text-[#64748B] block mt-0.5">Platform Administrator</span>
                  </div>
                </button>

                {showUserDropdown && (
                  <div className="absolute right-0 mt-2 w-48 bg-[#121722] border border-[#1E2638] rounded-[10px] shadow-2xl p-2 z-50 space-y-1 text-[12px] font-bold">
                    <div className="px-3 py-2 border-b border-[#1E2638]">
                      <span className="text-white block truncate">Super Admin Account</span>
                      <span className="text-[10px] text-[#64748B] block font-mono truncate">{user.email}</span>
                    </div>

                    <Link
                      href="/platform/profile"
                      onClick={() => setShowUserDropdown(false)}
                      className="flex items-center gap-2 px-3 py-2 hover:bg-[#1A2234] text-[#E1E7F0] hover:text-[#2E9D50] rounded-[6px] transition-colors"
                    >
                      <User className="w-4 h-4 text-[#2E9D50]" />
                      <span>My Profile</span>
                    </Link>

                    <Link
                      href="/platform/security"
                      onClick={() => setShowUserDropdown(false)}
                      className="flex items-center gap-2 px-3 py-2 hover:bg-[#1A2234] text-[#E1E7F0] hover:text-[#2E9D50] rounded-[6px] transition-colors"
                    >
                      <Shield className="w-4 h-4 text-[#2E9D50]" />
                      <span>My Security</span>
                    </Link>

                    <button
                      onClick={() => logout()}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[#3B1516] text-[#E53935] rounded-[6px] transition-colors text-left"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </header>

          {/* Main Dashboard Body */}
          <div className="flex-1 p-6 space-y-6 max-w-[1600px] w-full mx-auto">
            {children}
          </div>
        </main>
      </div>

      {/* Bottom Session / Status Bar */}
      <footer className="bg-[#0B0E14] border-t border-[#1E2638] px-6 py-2 text-[10px] text-[#64748B] font-mono flex flex-col sm:flex-row items-center justify-between gap-2 z-30">
        <div className="flex items-center gap-4">
          <span>Logged in as: <strong className="text-white">{user.email}</strong></span>
          <span>Role: <strong className="text-[#2E9D50]">SUPER_ADMIN</strong></span>
          <span>Scope: <strong className="text-[#2E9D50]">GLOBAL PLATFORM</strong></span>
        </div>
        <div className="flex items-center gap-4">
          <span>Last Login: Sep 1, 2026 10:24 AM</span>
          <span className="flex items-center gap-1 text-[#2E9D50] font-bold">
            <span className="w-2 h-2 rounded-full bg-[#2E9D50] animate-pulse" /> Session: Active
          </span>
        </div>
      </footer>
    </div>
  );
}
