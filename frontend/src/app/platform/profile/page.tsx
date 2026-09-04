"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  User,
  Shield,
  Key,
  RefreshCw,
  CheckCircle,
  Globe,
  Lock,
  Clock,
  ShieldCheck,
  Building,
  Mail,
  Sliders,
  UserCheck
} from "lucide-react";

export default function PlatformProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/profile");
      setProfile(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Super Admin Platform Profile</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              GLOBAL PLATFORM OWNER
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Global platform owner identity, credentials, and authentication scopes.
          </p>
        </div>

        <button
          onClick={() => loadProfile()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* MAIN PREMIUM PROFILE CARD */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[16px] p-6 space-y-6 shadow-xl max-w-4xl">
        {/* Banner Section */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-[12px] bg-[#173B25] text-[#2E9D50] border-2 border-[#2E9D50] font-bold flex items-center justify-center text-[22px] shadow-lg shrink-0">
              SA
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-3 flex-wrap">
                <h2 className="text-[22px] font-bold text-white">{profile?.full_name || "Super Admin Account"}</h2>
                <span className="px-3 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
                  SUPER_ADMIN
                </span>
              </div>
              <div className="flex items-center gap-2 text-[13px] text-[#94A3B8] font-mono">
                <Mail className="w-3.5 h-3.5 text-[#64748B]" />
                <span>{profile?.email || "thefreelancer2076@gmail.com"}</span>
              </div>
            </div>
          </div>

          <div className="px-3 py-1.5 bg-[#161C2A] rounded-[8px] border border-[#232F48] text-right font-mono text-[11px] shrink-0">
            <span className="text-[#64748B] block">Role Privilege Level</span>
            <span className="font-bold text-[#2E9D50] text-[13px]">Level 9 (Super Admin)</span>
          </div>
        </div>

        {/* METRICS & SCOPE CARDS GRID */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-[13px]">
          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">Organization Scope</span>
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-[#2E9D50]" />
              <p className="font-bold text-white text-[15px]">{profile?.organization || "GLOBAL PLATFORM"}</p>
            </div>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">Platform Privileges</span>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#2E9D50]" />
              <p className="font-bold text-[#2E9D50] text-[15px]">{profile?.scope || "ALL ORGANIZATIONS"}</p>
            </div>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">Account Status</span>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-[#2E9D50]" />
              <p className="font-bold text-[#2E9D50] text-[15px]">{profile?.status || "ACTIVE"}</p>
            </div>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">Auth Provider</span>
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#2E9D50]" />
              <p className="font-bold text-white text-[15px]">{profile?.provider || "Supabase Auth"}</p>
            </div>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">Multi-Factor Auth (MFA)</span>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-[#2E9D50]" />
              <p className="font-bold text-white text-[15px]">Enforced (Hardware/TOTP)</p>
            </div>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono block">Session Status</span>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-[#2E9D50]" />
              <p className="font-bold text-[#2E9D50] text-[15px]">Active & Verified</p>
            </div>
          </div>
        </div>

        {/* SECURITY & CREDENTIALS INFO */}
        <div className="bg-[#161C2A] border border-[#232F48] rounded-[12px] p-5 space-y-3">
          <h3 className="font-bold text-white text-[14px] uppercase font-mono text-[#2E9D50]">
            Global Credentials & Security Scopes
          </h3>

          <div className="space-y-2 text-[12px]">
            <div className="flex items-center justify-between p-2.5 bg-[#121722] rounded-[6px] border border-[#1E2638]">
              <span className="text-[#94A3B8]">Super Admin Identity ID</span>
              <span className="font-mono text-white font-bold">{profile?.id || "sa-00000-00000-00000"}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 bg-[#121722] rounded-[6px] border border-[#1E2638]">
              <span className="text-[#94A3B8]">Password Credential</span>
              <span className="font-mono text-[#64748B] font-bold">•••••••••••• (Encrypted with bcrypt)</span>
            </div>
            <div className="flex items-center justify-between p-2.5 bg-[#121722] rounded-[6px] border border-[#1E2638]">
              <span className="text-[#94A3B8]">Cross-Tenant Isolation Bypass</span>
              <span className="font-mono text-[#2E9D50] font-bold">GRANTED (Full Read/Write Platform Administrative Rights)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
