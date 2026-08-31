"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { FileText, Download, ArrowLeft, Clock } from "lucide-react";

export default function ReportHistoryPage() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHistory() {
      setLoading(true);
      try {
        const data = await fetchApi("/reports/history").catch(() => []);
        setHistory(data || []);
      } catch (err) {
        console.error("Failed to load report history:", err);
      } finally {
        setLoading(false);
      }
    }
    loadHistory();
  }, []);

  const handleDownload = (reportId: string, filename: string) => {
    const token = localStorage.getItem("token");
    const downloadUrl = `http://localhost:8000/api/v1/reports/download/${reportId}`;

    fetch(downloadUrl, {
      headers: { Authorization: `Bearer ${token}` },
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
      .catch((err) => console.error("Download error:", err));
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3">
            <Link href="/reports" className="text-[#666666] hover:text-[#1F1F1F]">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">Report Generation History</h1>
          </div>
          <p className="text-[13px] text-[#666666] mt-1">
            Complete audit trail of all generated subsystem reports scoped to your organization.
          </p>
        </div>

        <Link
          href="/reports"
          className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[13px] font-bold rounded-[8px] transition-colors"
        >
          + Generate New Report
        </Link>
      </div>

      {/* History Table */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-[#666666] font-bold animate-pulse">Loading report history...</div>
        ) : history.length === 0 ? (
          <div className="p-8 text-center text-[#666666]">No generated reports found in history.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#E8E8E4] text-[#666666] font-bold uppercase text-[11px]">
                  <th className="py-2.5">Report Title</th>
                  <th className="py-2.5">Subsystem Type</th>
                  <th className="py-2.5">Format</th>
                  <th className="py-2.5">Size</th>
                  <th className="py-2.5">Generated At</th>
                  <th className="py-2.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E8E4]">
                {history.map((h) => (
                  <tr key={h.id} className="hover:bg-[#FCFCFA]">
                    <td className="py-3 font-bold text-[#1F1F1F]">{h.title}</td>
                    <td className="py-3 font-mono text-[12px] text-[#666666]">{h.report_type}</td>
                    <td className="py-3">
                      <span className="px-2.5 py-0.5 bg-[#F1EDFA] text-[#8064C8] font-bold rounded text-[11px] border border-[#8064C8]/20 uppercase">
                        {h.file_format}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-[12px]">{Math.round(h.file_size_bytes / 1024)} KB</td>
                    <td className="py-3 text-[#666666] text-[12px]">
                      {h.created_at ? new Date(h.created_at).toLocaleString() : "-"}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleDownload(h.id, `${h.title}.${h.file_format.toLowerCase()}`)}
                        className="px-3 py-1 bg-[#EAF7EE] text-[#237A3C] hover:bg-[#2E9D50] hover:text-white font-bold rounded-[6px] text-[12px] transition-colors inline-flex items-center gap-1.5"
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
