import React from "react";
import SidebarNav from "@/components/ui/SidebarNav";
import DashboardHeader from "@/components/ui/DashboardHeader";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#FCFCFA] flex">
      {/* Sidebar Navigation */}
      <SidebarNav />

      {/* Main Content Area */}
      <main className="flex-1 ml-64 p-8 min-h-screen overflow-y-auto">
        <div className="max-w-[1400px] mx-auto space-y-6">
          <DashboardHeader />
          {children}
        </div>
      </main>
    </div>
  );
}
