"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { ShieldAlert, ArrowLeft, Lock } from "lucide-react";
import { useAuth } from "@/lib/useAuth";

export default function ForbiddenPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-[#FCFCFA] text-[#1F1F1F] font-serif flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-md w-full bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] p-8 shadow-xl space-y-6">
        {/* Header Icon Badge */}
        <div className="w-16 h-16 bg-[#FDECEC] border border-[#E53935]/30 rounded-full flex items-center justify-center mx-auto text-[#E53935]">
          <ShieldAlert className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <span className="text-[11px] font-bold text-[#E53935] uppercase tracking-widest bg-[#FDECEC] px-3 py-1 rounded-full border border-[#E53935]/30">
            HTTP 403 — Access Restricted
          </span>
          <h1 className="text-[26px] font-bold text-[#1F1F1F]">Permission Denied</h1>
          <p className="text-[13px] text-[#666666] leading-relaxed">
            You do not have permission to access this enterprise resource or page.
          </p>
        </div>

        {/* User Role Diagnostic Box */}
        <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] text-left text-[12px] space-y-2">
          <div className="flex items-center justify-between text-[#666666]">
            <span>Authenticated User:</span>
            <span className="font-bold text-[#1F1F1F]">{user?.full_name || "Enterprise User"}</span>
          </div>
          <div className="flex items-center justify-between text-[#666666]">
            <span>Assigned Role:</span>
            <span className="font-bold text-[#8064C8]">{user?.role || "USER"}</span>
          </div>
          <div className="flex items-center justify-between text-[#666666]">
            <span>Organization:</span>
            <span className="font-mono text-[#1F1F1F] text-[11px]">{user?.org_name || "AgentGuard Enterprise"}</span>
          </div>
        </div>

        <p className="text-[11px] text-[#666666] italic">
          If you require access to this section, please contact your Organization Administrator to upgrade your IAM role.
        </p>

        {/* Action Button */}
        <div className="pt-2">
          <Link
            href="/dashboard"
            className="w-full py-2.5 bg-[#1F1F1F] text-[#FFFFFF] text-[13px] font-bold rounded-[8px] hover:bg-[#333333] transition-colors flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Safe Dashboard</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
