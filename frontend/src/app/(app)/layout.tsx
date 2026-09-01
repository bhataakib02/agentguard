"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Menu, X } from "lucide-react";
import SidebarNav from "@/components/ui/SidebarNav";
import DashboardHeader from "@/components/ui/DashboardHeader";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#FCFCFA] flex flex-col lg:flex-row">
      {/* Mobile Top Bar (< lg screens) */}
      <div className="lg:hidden sticky top-0 z-30 bg-[#FFFFFF] border-b border-[#E8E8E4] px-4 py-3 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
            className="p-2 text-[#1F1F1F] hover:bg-[#FCFCFA] rounded-[8px] border border-[#E8E8E4]"
            aria-label="Toggle Navigation Menu"
          >
            {mobileSidebarOpen ? <X className="w-5 h-5 text-[#E53935]" /> : <Menu className="w-5 h-5" />}
          </button>
          <Link href="/dashboard" className="flex items-center gap-2">
            <Image src="/logo.png" alt="AGENTGUARD Logo" width={24} height={24} className="object-contain" />
            <span className="font-bold text-[16px] text-[#1F1F1F]">AGENTGUARD</span>
          </Link>
        </div>

        <span className="text-[10px] font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded">
          CONTROL PLANE
        </span>
      </div>

      {/* Sidebar Navigation */}
      <SidebarNav isOpen={mobileSidebarOpen} onClose={() => setMobileSidebarOpen(false)} />

      {/* Main Content Area */}
      <main className="flex-1 lg:ml-64 p-4 sm:p-6 lg:p-8 min-h-screen overflow-x-hidden">
        <div className="max-w-[1400px] mx-auto space-y-6">
          <DashboardHeader />
          {children}
        </div>
      </main>
    </div>
  );
}
