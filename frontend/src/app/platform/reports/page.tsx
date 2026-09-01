"use client";

import React, { useState } from "react";
import { fetchApi } from "@/lib/api";
import { FileText, Download, FileSpreadsheet, RefreshCw, CheckCircle } from "lucide-react";

export default function PlatformReportsPage() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (format: "pdf" | "excel" | "csv", reportType: string) => {
    setDownloading(reportType + "-" + format);
    try {
      const endpoint = format === "pdf" ? "/reports/export/pdf" : format === "excel" ? "/reports/export/excel" : "/reports/export/csv";
      const token = localStorage.getItem("agentguard_token");
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const res = await fetch(`${baseUrl}${endpoint}?type=${reportType}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Failed to export report.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `AGENTGUARD_${reportType.toUpperCase()}_REPORT.${format === "excel" ? "xlsx" : format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(err.message || "Report download failed.");
    } finally {
      setDownloading(null);
    }
  };

  const reportCards = [
    { title: "Complete Platform Report", type: "platform_summary", desc: "Global breakdown of tenant organizations, SaaS licenses, active AI agents, and overall system health." },
    { title: "Organization Directory Report", type: "organizations", desc: "Detailed listing of all customer tenant organizations, subscription plans, and admin email contacts." },
    { title: "Global Users Audit Report", type: "users", desc: "Comprehensive user account roster across all organizations, role levels, and account statuses." },
    { title: "AI Agents Governance Roster", type: "agents", desc: "Catalog of all registered machine AI agents, autonomy tiers, risk scores, and circuit breaker states." },
    { title: "SaaS Licensing & Expiry Roster", type: "licenses", desc: "Subscription license plans, expiration dates, seat usage percentages, and renewal timelines." },
    { title: "Platform Security & Incidents Report", type: "security", desc: "Security incidents, critical risk flags, blocked actions, and emergency kill-switch events." }
  ];

  return (
    <div className="space-y-6">
      <div className="border-b border-[#1E2638] pb-4">
        <h1 className="text-[22px] font-bold text-white tracking-tight">Platform Report Center</h1>
        <p className="text-[12px] text-[#64748B]">Generate and export real database-driven executive reports in PDF, Excel, and CSV formats</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {reportCards.map((rc) => (
          <div key={rc.type} className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm hover:border-[#2E9D50]/50 transition-colors flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[#2E9D50]">
                <FileText className="w-5 h-5" />
                <h3 className="font-bold text-white text-[16px]">{rc.title}</h3>
              </div>
              <p className="text-[12px] text-[#94A3B8] leading-relaxed">{rc.desc}</p>
            </div>

            <div className="flex items-center gap-2 pt-3 border-t border-[#1E2638]">
              <button
                onClick={() => handleDownload("pdf", rc.type)}
                disabled={downloading === rc.type + "-pdf"}
                className="flex-1 py-2 bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 rounded-[8px] text-[11px] font-bold hover:bg-[#2E9D50] hover:text-white transition-colors flex items-center justify-center gap-1.5"
              >
                {downloading === rc.type + "-pdf" ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                <span>PDF Report</span>
              </button>

              <button
                onClick={() => handleDownload("excel", rc.type)}
                disabled={downloading === rc.type + "-excel"}
                className="flex-1 py-2 bg-[#161C2A] text-[#0284C7] border border-[#232F48] rounded-[8px] text-[11px] font-bold hover:bg-[#1A2234] transition-colors flex items-center justify-center gap-1.5"
              >
                {downloading === rc.type + "-excel" ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                <span>Excel XLSX</span>
              </button>

              <button
                onClick={() => handleDownload("csv", rc.type)}
                disabled={downloading === rc.type + "-csv"}
                className="px-3 py-2 bg-[#161C2A] text-[#94A3B8] border border-[#232F48] rounded-[8px] text-[11px] font-bold hover:bg-[#1A2234] hover:text-white transition-colors"
              >
                CSV
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
