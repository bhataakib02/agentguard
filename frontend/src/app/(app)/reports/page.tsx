"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import {
  FileText,
  Download,
  Calendar,
  Filter,
  CheckCircle,
  FileSpreadsheet,
  FileCode,
  Clock,
  Plus,
  Shield,
  Bot,
  Users,
  Activity,
  DollarSign
} from "lucide-react";

export default function ReportCenterPage() {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [scheduled, setScheduled] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const [selectedReportType, setSelectedReportType] = useState("EXECUTIVE");
  const [selectedFormat, setSelectedFormat] = useState("PDF");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [notice, setNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    async function loadReportsData() {
      setLoading(true);
      try {
        const [catData, histData, schedData] = await Promise.all([
          fetchApi("/reports").catch(() => []),
          fetchApi("/reports/history").catch(() => []),
          fetchApi("/reports/scheduled").catch(() => []),
        ]);
        setCatalog(catData || []);
        setHistory(histData || []);
        setScheduled(schedData || []);
      } catch (err) {
        console.error("Failed to load report center data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadReportsData();
  }, []);

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerating(true);
    setNotice(null);

    try {
      const res = await fetchApi("/reports/generate", {
        method: "POST",
        body: JSON.stringify({
          report_type: selectedReportType,
          file_format: selectedFormat,
          date_from: dateFrom || null,
          date_to: dateTo || null,
        }),
      });

      setNotice({
        type: "success",
        message: `Successfully generated ${res.title} (${res.file_format}) from live database records!`,
      });

      // Refresh history list
      const updatedHist = await fetchApi("/reports/history").catch(() => []);
      setHistory(updatedHist || []);
    } catch (err: any) {
      setNotice({
        type: "error",
        message: err.message || "Failed to generate report.",
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadReport = (reportId: string, filename: string) => {
    const token = localStorage.getItem("token");
    const downloadUrl = `http://localhost:8000/api/v1/reports/download/${reportId}`;
    
    // Trigger download
    fetch(downloadUrl, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then((res) => res.blob())
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename || "report.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch((err) => console.error("Download failed:", err));
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-[#666666] font-bold animate-pulse">
        Loading AGENTGUARD Enterprise Report Center & Subsystem Catalog...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">Enterprise Report Center</h1>
            <span className="text-[11px] font-bold px-3 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded-full uppercase">
              Database Driven
            </span>
          </div>
          <p className="text-[13px] text-[#666666] mt-1">
            Generate narrative PDF summaries, tabular Excel workbooks, and raw CSV datasets derived from live database records.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/reports/history"
            className="px-4 py-2 bg-[#FCFCFA] border border-[#E8E8E4] text-[#1F1F1F] text-[13px] font-bold rounded-[8px] hover:bg-[#F0F0ED] transition-colors"
          >
            Report History
          </Link>
          <Link
            href="/reports/scheduled"
            className="px-4 py-2 bg-[#8064C8] hover:bg-[#6C52B0] text-white text-[13px] font-bold rounded-[8px] transition-colors"
          >
            Scheduled Delivery
          </Link>
        </div>
      </div>

      {/* Report Center Quick Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">Total Generated Reports</span>
          <span className="text-[24px] font-bold text-[#1F1F1F] block">{history.length}</span>
          <span className="text-[11px] text-[#2E9D50] font-bold">Tenant Isolated Scope</span>
        </div>

        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">Report Subsystems</span>
          <span className="text-[24px] font-bold text-[#8064C8] block">{catalog.length} Types</span>
          <span className="text-[11px] text-[#666666]">Executive, IAM, Security, Audit</span>
        </div>

        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">Scheduled Deliveries</span>
          <span className="text-[24px] font-bold text-[#1F1F1F] block">{scheduled.length} Active</span>
          <span className="text-[11px] text-[#237A3C] font-bold">Automated Email Audits</span>
        </div>

        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-2 shadow-sm">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">Supported Formats</span>
          <div className="flex items-center gap-2 pt-1">
            <span className="text-[11px] font-bold px-2 py-0.5 bg-[#F1EDFA] text-[#8064C8] rounded border border-[#8064C8]/20">PDF</span>
            <span className="text-[11px] font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] rounded border border-[#2E9D50]/20">EXCEL</span>
            <span className="text-[11px] font-bold px-2 py-0.5 bg-[#F0F0ED] text-[#1F1F1F] rounded border border-[#E8E8E4]">CSV</span>
          </div>
          <span className="text-[11px] text-[#666666] block pt-1">No Static Screenshots</span>
        </div>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div className={`p-4 rounded-[8px] text-[13px] font-bold border flex items-center gap-2 ${
          notice.type === "success"
            ? "bg-[#EAF7EE] border-[#2E9D50]/30 text-[#237A3C]"
            : "bg-[#FDECEC] border-[#E53935]/30 text-[#C62828]"
        }`}>
          <CheckCircle className="w-4 h-4" />
          <span>{notice.message}</span>
        </div>
      )}

      {/* Interactive Report Generator Form */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#8064C8]" />
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Generate New Enterprise Report</h2>
          </div>
          <span className="text-[11px] font-bold text-[#666666] uppercase">Live Database Query</span>
        </div>

        <form onSubmit={handleGenerateReport} className="space-y-6 text-[13px]">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Report Type Selector */}
            <div>
              <label className="block font-bold text-[#1F1F1F] mb-1">Select Report Subsystem</label>
              <select
                value={selectedReportType}
                onChange={(e) => setSelectedReportType(e.target.value)}
                className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#8064C8] font-bold text-[#1F1F1F]"
              >
                {catalog.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title} ({r.category})
                  </option>
                ))}
              </select>
            </div>

            {/* Output Format Picker */}
            <div>
              <label className="block font-bold text-[#1F1F1F] mb-1">Export Format</label>
              <div className="grid grid-cols-3 gap-2">
                {["PDF", "EXCEL", "CSV"].map((fmt) => (
                  <button
                    type="button"
                    key={fmt}
                    onClick={() => setSelectedFormat(fmt)}
                    className={`py-2 rounded-[8px] font-bold text-[12px] border transition-colors ${
                      selectedFormat === fmt
                        ? "bg-[#8064C8] text-white border-[#8064C8]"
                        : "bg-[#FCFCFA] text-[#1F1F1F] border-[#E8E8E4] hover:bg-[#F0F0ED]"
                    }`}
                  >
                    {fmt}
                  </button>
                ))}
              </div>
            </div>

            {/* Date Range Picker */}
            <div>
              <label className="block font-bold text-[#1F1F1F] mb-1">Date Range (Optional)</label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="px-2 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none text-[12px]"
                />
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="px-2 py-1.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none text-[12px]"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-[#E8E8E4]">
            <span className="text-[12px] text-[#666666]">
              Reports are automatically scoped to your active tenant boundary and audited.
            </span>
            <button
              type="submit"
              disabled={generating}
              className="flex items-center gap-2 px-6 py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[8px] transition-colors shadow-sm"
            >
              <FileText className="w-4 h-4" />
              <span>{generating ? "Generating Database Report..." : "Generate Report"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Recent Generated Reports Table */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
          <h2 className="text-[18px] font-bold text-[#1F1F1F]">Recent Generated Reports</h2>
          <Link href="/reports/history" className="text-[12px] font-bold text-[#8064C8] hover:underline">
            View All History →
          </Link>
        </div>

        {history.length === 0 ? (
          <p className="text-[13px] text-[#666666] italic py-4 text-center">
            No reports generated yet. Select a subsystem report type above to generate your first document.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#E8E8E4] text-[#666666] font-bold uppercase text-[11px]">
                  <th className="py-2.5">Report Title</th>
                  <th className="py-2.5">Subsystem</th>
                  <th className="py-2.5">Format</th>
                  <th className="py-2.5">File Size</th>
                  <th className="py-2.5">Generated At</th>
                  <th className="py-2.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E8E4]">
                {history.slice(0, 5).map((h) => (
                  <tr key={h.id} className="hover:bg-[#FCFCFA]">
                    <td className="py-3 font-bold text-[#1F1F1F]">{h.title}</td>
                    <td className="py-3 font-mono text-[12px] text-[#666666]">{h.report_type}</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 bg-[#F1EDFA] text-[#8064C8] font-bold rounded text-[11px] border border-[#8064C8]/20 uppercase">
                        {h.file_format}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-[12px]">{Math.round(h.file_size_bytes / 1024)} KB</td>
                    <td className="py-3 text-[#666666] text-[12px]">
                      {h.created_at ? new Date(h.created_at).toLocaleString() : "-"}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleDownloadReport(h.id, `${h.title}.${h.file_format.toLowerCase()}`)}
                        className="px-3 py-1 bg-[#EAF7EE] text-[#237A3C] hover:bg-[#2E9D50] hover:text-white font-bold rounded-[6px] text-[12px] transition-colors flex items-center gap-1.5 ml-auto"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
