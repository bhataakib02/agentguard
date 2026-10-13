"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Shield, GitFork, Activity, Play, CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // PACE Form State
  const [selectedAgentCode, setSelectedAgentCode] = useState("");
  const [actionType, setActionType] = useState("READ");
  const [targetResource, setTargetResource] = useState("orders");
  const [operation, setOperation] = useState("query_records");
  const [amount, setAmount] = useState<number>(0);
  const [prompt, setPrompt] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [enforcing, setEnforcing] = useState(false);
  const [paceResult, setPaceResult] = useState<any>(null);

  const loadDecisions = async () => {
    try {
      const [decData, agData] = await Promise.all([
        fetchApi("/decisions").catch(() => []),
        fetchApi("/agents").catch(() => [])
      ]);
      setDecisions(decData || []);
      setAgents(agData || []);
      if (agData && agData.length > 0 && !selectedAgentCode) {
        setSelectedAgentCode(agData[0].agent_code);
      }
    } catch (err) {
      console.error("Decisions fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDecisions();
  }, []);

  const handleEvaluate = async (executeBoundary: boolean = false) => {
    if (!selectedAgentCode) {
      alert("Please select a registered AI agent first.");
      return;
    }

    if (executeBoundary) {
      setEnforcing(true);
    } else {
      setEvaluating(true);
    }
    setPaceResult(null);

    const endpoint = executeBoundary ? "/decisions/control/execute" : "/decisions/control/evaluate";
    const payload = {
      agent_code: selectedAgentCode,
      action_type: actionType,
      target_resource: targetResource,
      operation: operation,
      amount: Number(amount) || 0.0,
      prompt: prompt || `${actionType} on ${targetResource} ${operation}`.trim()
    };

    try {
      const res = await fetchApi(endpoint, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setPaceResult(res);
      await loadDecisions();
    } catch (err: any) {
      alert(`Action Control Engine Error: ${err.message}`);
    } finally {
      setEvaluating(false);
      setEnforcing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Predictive Action Control Engine (PACE)</h1>
        <p className="text-[13px] text-[#666666]">
          Real-Time Action Boundary Enforcement, Sequence-Aware Risk Assessment & Decision Black Box Stream
        </p>
      </div>

      {/* PACE Interactive Control Console */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#2E9D50]" />
            <h2 className="text-[16px] font-bold text-[#1F1F1F]">Action Control Evaluation & Enforcement Gate</h2>
          </div>
          <span className="text-[11px] font-bold px-2.5 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded-full">
            PACE Phase 1 Kernel Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-[13px]">
          <div>
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Authenticated AI Agent</label>
            <select
              value={selectedAgentCode}
              onChange={(e) => setSelectedAgentCode(e.target.value)}
              className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[#1F1F1F] font-bold focus:outline-none focus:border-[#2E9D50]"
            >
              {agents.map((ag) => (
                <option key={ag.id} value={ag.agent_code}>
                  {ag.name} ({ag.agent_code}) - {ag.autonomy_level}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Action Type</label>
            <select
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
              className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[#1F1F1F] font-bold focus:outline-none focus:border-[#2E9D50]"
            >
              <option value="READ">READ (Database Query / Fetch)</option>
              <option value="EXECUTE">EXECUTE (API / Tool Dispatch)</option>
              <option value="WRITE">WRITE (Create / Update Record)</option>
              <option value="DELETE">DELETE (Remove Resource / Drop)</option>
              <option value="TRANSFER">TRANSFER (Financial Egress)</option>
              <option value="EXPORT">EXPORT (Data Exfiltration)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Target Resource</label>
            <input
              type="text"
              value={targetResource}
              onChange={(e) => setTargetResource(e.target.value)}
              placeholder="e.g. orders, payments, production_db"
              className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Amount (₹ INR)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              placeholder="0.00"
              className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[#1F1F1F] font-bold focus:outline-none focus:border-[#2E9D50]"
            />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          <div className="w-full sm:w-2/3">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Optional natural intent or contextual description (e.g. 'Read quarterly customer orders')"
              className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <button
              onClick={() => handleEvaluate(false)}
              disabled={evaluating || enforcing}
              className="px-4 py-2.5 bg-[#FCFCFA] hover:bg-[#F0F0EE] text-[#1F1F1F] border border-[#E8E8E4] text-[13px] font-bold rounded-[8px] transition-colors disabled:opacity-50"
            >
              {evaluating ? "Evaluating..." : "Pre-Flight Evaluate"}
            </button>
            <button
              onClick={() => handleEvaluate(true)}
              disabled={evaluating || enforcing}
              className="px-5 py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white text-[13px] font-bold rounded-[8px] flex items-center gap-2 transition-colors disabled:opacity-50 shadow-sm"
            >
              <Play className="w-4 h-4" />
              <span>{enforcing ? "Enforcing..." : "Evaluate & Enforce"}</span>
            </button>
          </div>
        </div>

        {/* PACE Real-Time Decision Card */}
        {paceResult && (
          <div className="border border-[#E8E8E4] rounded-[10px] bg-[#FCFCFA] p-5 space-y-4">
            {(() => {
              const evalData = paceResult.evaluation || paceResult;
              const isExec = Boolean(paceResult.executed !== undefined);
              return (
                <>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E8E8E4] pb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-[12px] font-bold text-[#666666] uppercase">PACE Decision:</span>
                      <StatusBadge status={evalData.decision} />
                      {isExec && (
                        <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                          paceResult.executed
                            ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
                            : paceResult.execution_status === "PENDING_APPROVAL"
                            ? "bg-[#FFF4D9] text-[#A56300] border-[#F59A23]/30"
                            : "bg-[#FDECEC] text-[#C62828] border-[#E53935]/30"
                        }`}>
                          Boundary: {paceResult.execution_status}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[12px]">
                      <span className="text-[#666666]">Risk Score:</span>
                      <span className={`font-bold ${
                        evalData.risk_score > 60 ? "text-[#E53935]" : evalData.risk_score > 30 ? "text-[#F59A23]" : "text-[#2E9D50]"
                      }`}>
                        {evalData.risk_score}/100 ({evalData.risk_level})
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[12px]">
                    <div className="space-y-1">
                      <span className="font-bold text-[#1F1F1F] block">Reason & Policy Applied:</span>
                      <p className="text-[#666666]">{evalData.reason}</p>
                      <span className="text-[11px] font-mono text-[#8064C8] block mt-1">
                        Policy: {evalData.policy_applied || "Global Safety Policy"}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <span className="font-bold text-[#1F1F1F] block">Sequence-Aware Risk Assessment:</span>
                      <p className="text-[#666666]">{evalData.sequence_indicators?.explanation}</p>
                      {evalData.sequence_indicators?.patterns_detected?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {evalData.sequence_indicators.patterns_detected.map((p: any, idx: number) => (
                            <span key={idx} className="text-[10px] font-bold px-2 py-0.5 bg-[#FFF4D9] text-[#A56300] border border-[#F59A23]/30 rounded">
                              ⚠ {p.pattern_name} (+{p.risk_delta})
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {evalData.execution_gate_token && (
                    <div className="pt-2 border-t border-[#E8E8E4] flex items-center justify-between text-[11px] font-mono text-[#666666]">
                      <span>Gate Token: {evalData.execution_gate_token}</span>
                      <span>Correlation ID: {evalData.correlation_id}</span>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}
      </div>

      {/* Decision Black Box Stream Table */}
      <div className="space-y-4">
        <h3 className="text-[18px] font-bold text-[#1F1F1F]">Immutable Decision Black Box Stream</h3>
        {decisions.length === 0 ? (
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
            <Shield className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
            <h4 className="text-[16px] font-bold text-[#1F1F1F]">Zero Decisions Recorded</h4>
            <p className="text-[12px] text-[#666666]">
              No governance decisions exist in the database. Use the Action Control Console above to evaluate actions.
            </p>
          </div>
        ) : (
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-x-auto shadow-sm">
            <table className="w-full text-left border-collapse text-[13px]">
              <thead>
                <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                  <th className="p-4">ACTION</th>
                  <th className="p-4">RESOURCE TARGET</th>
                  <th className="p-4">AMOUNT</th>
                  <th className="p-4">DECISION</th>
                  <th className="p-4">POLICY APPLIED</th>
                  <th className="p-4 text-right">PROVENANCE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E8E4]">
                {decisions.map((dec) => (
                  <tr key={dec.id} className="hover:bg-[#FCFCFA] transition-colors">
                    <td className="p-4 font-bold text-[#1F1F1F]">{dec.action_requested}</td>
                    <td className="p-4 text-[#666666]">{dec.resource_target}</td>
                    <td className="p-4 font-bold text-[#2E9D50]">₹{dec.amount ? dec.amount.toLocaleString() : "0"}.00</td>
                    <td className="p-4"><StatusBadge status={dec.decision} /></td>
                    <td className="p-4 text-[12px] text-[#666666]">{dec.policy_name}</td>
                    <td className="p-4 text-right">
                      <Link
                        href={`/provenance?id=${dec.id}`}
                        className="inline-flex items-center gap-1 text-[12px] font-bold text-[#8064C8] hover:underline"
                      >
                        <GitFork className="w-3.5 h-3.5" />
                        <span>Trace</span>
                      </Link>
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
