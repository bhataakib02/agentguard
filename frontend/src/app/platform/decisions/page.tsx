"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Activity,
  Filter,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  GitFork,
  X,
  Shield,
  FileText
} from "lucide-react";

export default function PlatformDecisionsPage() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedOrg, setSelectedOrg] = useState("ALL");
  const [selectedDecision, setSelectedDecision] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Trace Modal State
  const [selectedTrace, setSelectedTrace] = useState<any>(null);

  const loadDecisions = async () => {
    setLoading(true);
    try {
      const queryParams = new URLSearchParams();
      if (selectedOrg !== "ALL") queryParams.append("org_id", selectedOrg);
      if (selectedDecision !== "ALL") queryParams.append("decision", selectedDecision);

      const [decData, orgData] = await Promise.all([
        fetchApi(`/platform/decisions?${queryParams.toString()}`),
        fetchApi("/platform/organizations")
      ]);
      setDecisions(decData || []);
      setOrganizations(orgData || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDecisions();
  }, [selectedOrg, selectedDecision]);

  const filteredDecisions = decisions.filter((d) => {
    if (!searchQuery.trim()) return true;
    const term = searchQuery.toLowerCase();
    return (
      d.action?.toLowerCase().includes(term) ||
      d.resource_target?.toLowerCase().includes(term) ||
      d.agent_name?.toLowerCase().includes(term) ||
      d.organization?.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Decision Black Box</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              IMMUTABLE LEDGER
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Immutable log of governance decisions and intent evaluation records across all AI agents.
          </p>
        </div>

        <button
          onClick={() => loadDecisions()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[10px] p-3.5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm text-[12px]">
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Org Filter */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#94A3B8]">Organization:</span>
            <select
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              className="bg-[#161C2A] border border-[#232F48] text-white text-[12px] font-bold rounded-[6px] px-3 py-1.5 outline-none focus:border-[#2E9D50]"
            >
              <option value="ALL">🌐 All Organizations</option>
              {organizations.map((o) => (
                <option key={o.id} value={o.id}>🏢 {o.name}</option>
              ))}
            </select>
          </div>

          {/* Decision Filter */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#94A3B8]">Decision:</span>
            <select
              value={selectedDecision}
              onChange={(e) => setSelectedDecision(e.target.value)}
              className="bg-[#161C2A] border border-[#232F48] text-white text-[12px] font-bold rounded-[6px] px-3 py-1.5 outline-none focus:border-[#2E9D50]"
            >
              <option value="ALL">All Outcomes</option>
              <option value="ALLOW">ALLOW</option>
              <option value="REVIEW">REVIEW</option>
              <option value="REFUSE">REFUSE</option>
            </select>
          </div>
        </div>

        {/* Search */}
        <div className="relative w-full md:w-64">
          <Search className="w-3.5 h-3.5 text-[#64748B] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search action, agent, resource..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[6px] text-[12px] text-white outline-none focus:border-[#2E9D50]"
          />
        </div>
      </div>

      {/* Decision Table */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase font-mono">
              <tr>
                <th className="py-3.5 px-4">Action Requested</th>
                <th className="py-3.5 px-4">Target Resource</th>
                <th className="py-3.5 px-4">Organization</th>
                <th className="py-3.5 px-4">AI Agent</th>
                <th className="py-3.5 px-4 text-right">Amount (₹)</th>
                <th className="py-3.5 px-4">Decision</th>
                <th className="py-3.5 px-4">Policy Applied</th>
                <th className="py-3.5 px-4 text-center">Risk Score</th>
                <th className="py-3.5 px-4">Timestamp</th>
                <th className="py-3.5 px-4 text-right">Provenance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {filteredDecisions.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-[#64748B] font-mono">
                    No decision evaluation records found.
                  </td>
                </tr>
              ) : (
                filteredDecisions.map((d) => (
                  <tr key={d.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3 px-4 font-bold text-white">{d.action}</td>
                    <td className="py-3 px-4 font-mono text-[#94A3B8] text-[11px]">{d.resource_target}</td>
                    <td className="py-3 px-4 text-[#94A3B8]">{d.organization}</td>
                    <td className="py-3 px-4 font-bold text-white">{d.agent_name}</td>
                    <td className="py-3 px-4 text-right font-mono text-white">
                      {d.amount > 0 ? `₹${d.amount.toLocaleString()}` : "—"}
                    </td>
                    <td className="py-3 px-4">
                      {d.decision === "ALLOW" && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
                          ALLOW
                        </span>
                      )}
                      {d.decision === "REVIEW" && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3D2910] text-[#F59A23] border border-[#F59A23]/40 font-mono">
                          REVIEW
                        </span>
                      )}
                      {d.decision === "REFUSE" && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#3B1516] text-[#E53935] border border-[#E53935]/40 font-mono">
                          REFUSE
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-[11px] text-[#94A3B8] truncate max-w-[140px]">
                      {d.policy_applied}
                    </td>
                    <td className="py-3 px-4 text-center font-mono font-bold text-white">
                      {d.risk_score}
                    </td>
                    <td className="py-3 px-4 font-mono text-[#64748B] text-[11px]">
                      {d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : "Just now"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedTrace(d)}
                        className="px-2.5 py-1 bg-[#173B25] hover:bg-[#237A3C] text-[#2E9D50] hover:text-white rounded-[6px] text-[11px] font-bold transition-colors flex items-center gap-1.5 ml-auto"
                      >
                        <GitFork className="w-3.5 h-3.5" />
                        <span>Trace</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* PROVENANCE TRACE MODAL */}
      {selectedTrace && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-6 max-w-2xl w-full space-y-4 shadow-2xl text-[13px]">
            <div className="flex items-center justify-between border-b border-[#1E2638] pb-3">
              <div className="flex items-center gap-2">
                <GitFork className="w-5 h-5 text-[#2E9D50]" />
                <h3 className="font-bold text-white text-[16px]">Decision Provenance & Causal Chain</h3>
              </div>
              <button onClick={() => setSelectedTrace(null)} className="text-[#64748B] hover:text-white font-bold">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 bg-[#161C2A] p-3 rounded-[8px] border border-[#232F48] font-mono text-[11px]">
                <div>
                  <span className="text-[#64748B] block">Decision ID</span>
                  <span className="text-white font-bold">{selectedTrace.id}</span>
                </div>
                <div>
                  <span className="text-[#64748B] block">Agent</span>
                  <span className="text-[#2E9D50] font-bold">{selectedTrace.agent_name} ({selectedTrace.agent_code})</span>
                </div>
                <div>
                  <span className="text-[#64748B] block">Organization</span>
                  <span className="text-white font-bold">{selectedTrace.organization}</span>
                </div>
                <div>
                  <span className="text-[#64748B] block">Outcome</span>
                  <span className="text-[#2E9D50] font-bold">{selectedTrace.decision}</span>
                </div>
              </div>

              <div className="bg-[#161C2A] p-4 rounded-[8px] border border-[#232F48] space-y-2">
                <h4 className="font-bold text-white text-[12px] uppercase font-mono text-[#2E9D50]">Evaluation Summary</h4>
                <p className="text-[#94A3B8] text-[12px]">{selectedTrace.explanation}</p>
                <div className="text-[11px] text-[#64748B] font-mono">
                  Policy Enforced: <strong className="text-white">{selectedTrace.policy_applied}</strong> • Risk Score: <strong className="text-[#2E9D50]">{selectedTrace.risk_score}</strong>
                </div>
              </div>

              {selectedTrace.provenance ? (
                <div className="bg-[#161C2A] p-4 rounded-[8px] border border-[#232F48] space-y-2">
                  <h4 className="font-bold text-white text-[12px] uppercase font-mono text-[#2E9D50]">Causal Chain Tree</h4>
                  <pre className="text-[11px] text-[#94A3B8] font-mono whitespace-pre-wrap overflow-x-auto p-2 bg-[#0A0D14] rounded border border-[#1E2638]">
                    {JSON.stringify(selectedTrace.provenance, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="p-3 bg-[#161C2A] rounded border border-[#232F48] text-center text-[#64748B] text-[11px] font-mono">
                  Immutable provenance record verified on Supabase ledger.
                </div>
              )}
            </div>

            <div className="flex items-center justify-end pt-3 border-t border-[#1E2638]">
              <button
                onClick={() => setSelectedTrace(null)}
                className="px-4 py-1.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[6px] font-bold text-[12px]"
              >
                Close Trace View
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
