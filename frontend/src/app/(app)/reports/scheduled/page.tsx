"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { ArrowLeft, Clock, Plus, CheckCircle } from "lucide-react";

export default function ScheduledReportsPage() {
  const [scheduled, setScheduled] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [reportType, setReportType] = useState("EXECUTIVE");
  const [format, setFormat] = useState("PDF");
  const [frequency, setFrequency] = useState("WEEKLY");
  const [recipients, setRecipients] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    async function loadScheduled() {
      setLoading(true);
      try {
        const data = await fetchApi("/reports/scheduled").catch(() => []);
        setScheduled(data || []);
      } catch (err) {
        console.error("Failed to load scheduled reports:", err);
      } finally {
        setLoading(false);
      }
    }
    loadScheduled();
  }, []);

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setNotice(null);

    try {
      await fetchApi("/reports/schedule", {
        method: "POST",
        body: JSON.stringify({
          report_type: reportType,
          file_format: format,
          frequency: frequency,
          recipient_emails: recipients,
        }),
      });

      setNotice("Scheduled report delivery configured successfully!");
      setRecipients("");
      const updated = await fetchApi("/reports/scheduled").catch(() => []);
      setScheduled(updated || []);
    } catch (err: any) {
      setNotice(err.message || "Failed to schedule report");
    } finally {
      setSaving(false);
      setTimeout(() => setNotice(null), 4000);
    }
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
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">Scheduled Report Delivery</h1>
          </div>
          <p className="text-[13px] text-[#666666] mt-1">
            Configure automated daily, weekly, or monthly report generation and delivery for authorized stakeholders.
          </p>
        </div>
      </div>

      {/* Notice */}
      {notice && (
        <div className="p-4 rounded-[8px] bg-[#EAF7EE] border border-[#2E9D50]/30 text-[#237A3C] text-[13px] font-bold flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />
          <span>{notice}</span>
        </div>
      )}

      {/* Schedule Form */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
        <h2 className="text-[18px] font-bold text-[#1F1F1F]">Configure Recurring Schedule</h2>

        <form onSubmit={handleCreateSchedule} className="space-y-4 max-w-xl text-[13px]">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-[#1F1F1F] mb-1">Report Subsystem</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none font-bold"
              >
                <option value="EXECUTIVE">Executive Summary Report</option>
                <option value="SECURITY">Security & Threat Report</option>
                <option value="GOVERNANCE">Governance Decision Report</option>
                <option value="IAM">IAM Security Report</option>
                <option value="AUDIT">Audit Log Report</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-[#1F1F1F] mb-1">Delivery Frequency</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none font-bold"
              >
                <option value="DAILY">Daily (Every 24h at 08:00 UTC)</option>
                <option value="WEEKLY">Weekly (Every Monday at 09:00 UTC)</option>
                <option value="MONTHLY">Monthly (1st of every Month)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-[#1F1F1F] mb-1">Export Format</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none font-bold"
              >
                <option value="PDF">PDF Narrative Document</option>
                <option value="EXCEL">Excel (.xlsx) Tabular Workbook</option>
                <option value="CSV">CSV Raw Dataset</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-[#1F1F1F] mb-1">Recipient Email(s)</label>
              <input
                type="text"
                required
                placeholder="admin@acme.com, sec@acme.com"
                value={recipients}
                onChange={(e) => setRecipients(e.target.value)}
                className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none font-mono text-[12px]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-[#8064C8] hover:bg-[#6C52B0] text-white font-bold rounded-[8px] transition-colors"
          >
            <Clock className="w-4 h-4" />
            <span>{saving ? "Saving..." : "Create Schedule"}</span>
          </button>
        </form>
      </div>

      {/* Active Schedules Table */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
        <h2 className="text-[18px] font-bold text-[#1F1F1F]">Active Report Schedules</h2>

        {loading ? (
          <div className="p-6 text-center text-[#666666] font-bold animate-pulse">Loading schedules...</div>
        ) : scheduled.length === 0 ? (
          <div className="p-6 text-center text-[#666666]">No recurring report schedules configured yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#E8E8E4] text-[#666666] font-bold uppercase text-[11px]">
                  <th className="py-2.5">Title</th>
                  <th className="py-2.5">Subsystem</th>
                  <th className="py-2.5">Frequency</th>
                  <th className="py-2.5">Recipients</th>
                  <th className="py-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E8E4]">
                {scheduled.map((s) => (
                  <tr key={s.id} className="hover:bg-[#FCFCFA]">
                    <td className="py-3 font-bold text-[#1F1F1F]">{s.title}</td>
                    <td className="py-3 font-mono text-[12px]">{s.report_type}</td>
                    <td className="py-3 font-bold text-[#8064C8]">{s.frequency}</td>
                    <td className="py-3 font-mono text-[12px]">{s.recipient_emails}</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] font-bold rounded text-[11px] border border-[#2E9D50]/20">
                        {s.status}
                      </span>
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
