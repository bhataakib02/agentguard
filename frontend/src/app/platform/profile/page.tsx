"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { User, Shield, Key, RefreshCw, CheckCircle, Globe } from "lucide-react";

export default function PlatformProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProf() {
      setLoading(true);
      try {
        const data = await fetchApi("/platform/profile");
        setProfile(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadProf();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#1E2638] pb-4">
        <h1 className="text-[22px] font-bold text-white tracking-tight">Super Admin Platform Profile</h1>
        <p className="text-[12px] text-[#64748B]">Global Platform Owner identity, credentials, and authentication scopes</p>
      </div>

      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-6 space-y-6 shadow-sm max-w-3xl">
        <div className="flex items-center gap-4 border-b border-[#1E2638] pb-6">
          <div className="w-16 h-16 rounded-[12px] bg-[#173B25] text-[#2E9D50] border border-[#2E9D50] font-bold flex items-center justify-center text-[22px] shadow-sm">
            SA
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-[20px] font-bold text-white">{profile?.full_name || "Super Admin Account"}</h2>
              <span className="px-3 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
                SUPER_ADMIN
              </span>
            </div>
            <p className="text-[13px] text-[#94A3B8] font-mono mt-1">{profile?.email || "thefreelancer2076@gmail.com"}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-[13px]">
          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Organization Scope</span>
            <p className="font-bold text-white text-[15px]">{profile?.organization || "GLOBAL PLATFORM"}</p>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Platform Privileges</span>
            <p className="font-bold text-[#2E9D50] text-[15px]">{profile?.scope || "ALL ORGANIZATIONS"}</p>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Account Status</span>
            <p className="font-bold text-[#2E9D50] text-[15px]">{profile?.status || "ACTIVE"}</p>
          </div>

          <div className="bg-[#161C2A] border border-[#232F48] rounded-[10px] p-4 space-y-1">
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Auth Provider</span>
            <p className="font-bold text-white text-[15px]">{profile?.provider || "Supabase Auth"}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
