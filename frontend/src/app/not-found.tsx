"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, ShieldAlert, Home, Radio, Search } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#FCFCFA] flex flex-col items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Dynamic Animated Radar Ring Backdrop */}
      <div className="absolute w-[500px] h-[500px] rounded-full border border-[#2E9D50]/15 animate-ping opacity-25" style={{ animationDuration: '6s' }}></div>
      <div className="absolute w-[360px] h-[360px] rounded-full border border-[#8064C8]/20 animate-spin" style={{ animationDuration: '20s' }}></div>

      <div className="max-w-md w-full bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] p-8 text-center space-y-6 shadow-xl relative z-10">
        {/* Animated Brand Logo Container */}
        <div className="relative w-28 h-28 mx-auto flex items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-[#EAF7EE] animate-pulse border border-[#2E9D50]/30"></div>
          <div className="relative w-20 h-20 bg-white rounded-full p-2 border border-[#E8E8E4] shadow-md flex items-center justify-center">
            <Image
              src="/logo.png"
              alt="AgentGuard Logo"
              width={64}
              height={64}
              className="object-contain hover:scale-105 transition-transform"
            />
          </div>
          <div className="absolute -top-1 -right-1 p-1.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-full shadow-sm text-[#E53935]">
            <ShieldAlert className="w-4 h-4" />
          </div>
        </div>

        {/* 404 Header Badge & Title */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#FDECEC] border border-[#E53935]/30 rounded-full text-[11px] font-bold text-[#C62828] uppercase tracking-wider">
            <Radio className="w-3 h-3 animate-pulse text-[#E53935]" />
            <span>Error 404 • Resource Not Found</span>
          </div>
          <h1 className="text-[36px] font-black text-[#1F1F1F] tracking-tight">
            Lost in Autonomous Space
          </h1>
          <p className="text-[13px] text-[#666666] leading-relaxed">
            The requested control plane route or resource does not exist or has been relocated by governance policy.
          </p>
        </div>

        {/* Diagnostic Metadata Callout */}
        <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] p-3 text-[11px] font-mono text-left space-y-1 text-[#666666]">
          <div className="flex justify-between">
            <span className="text-[#8064C8] font-bold">STATUS:</span>
            <span className="text-[#E53935] font-bold">HTTP 404 NOT_FOUND</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#8064C8] font-bold">AGENTGUARD ENGINE:</span>
            <span>Zero-Trust Control Plane</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#8064C8] font-bold">SECURITY DISPATCH:</span>
            <span>Route Restricted / Unmapped</span>
          </div>
        </div>

        {/* Action Navigation Buttons */}
        <div className="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/dashboard"
            className="flex-1 py-2.5 px-4 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors shadow-sm"
          >
            <Home className="w-4 h-4" />
            <span>Return to Dashboard</span>
          </Link>
          <Link
            href="/login"
            className="py-2.5 px-4 bg-[#FFFFFF] border border-[#E8E8E4] hover:bg-[#FCFCFA] text-[#1F1F1F] rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-[#666666]" />
            <span>Sign In</span>
          </Link>
        </div>
      </div>

      {/* Footer System Brand Text */}
      <div className="mt-8 text-center text-[11px] text-[#666666] font-bold tracking-wider uppercase">
        AGENTGUARD Runtime Control Plane for Autonomous AI
      </div>
    </div>
  );
}
