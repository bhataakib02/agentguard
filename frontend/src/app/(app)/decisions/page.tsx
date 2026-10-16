"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Shield, GitFork, Activity, Play, CheckCircle2, AlertTriangle, XCircle, Clock, Compass, Target, ArrowRight, BarChart2 } from "lucide-react";

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
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
      const [decData, agData, metricsData] = await Promise.all([
        fetchApi("/decisions").catch(() => []),
        fetchApi("/agents").catch(() => []),
        fetchApi("/decisions/control/metrics").catch(() => null)
      ]);
      setDecisions(decData || []);
      setAgents(agData || []);
      setMetrics(metricsData);
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
          Phase 2: Predictive Intelligence, Action-Chain Reachability & Minimal-Intervention Planning
        </p>
      </div>

      {/* Benchmark Metrics Strip (Real API data) */}
      {metrics && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] p-4 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E8E8E4] pb-2.5 mb-3">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-[#2E9D50]" />
              <h3 className="text-[13px] font-bold text-[#1F1F1F]">PACE Benchmark Evaluation Metrics</h3>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded">
              Dataset: {metrics.dataset_type} ({metrics.total_scenarios} scenarios)
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-[12px]">
            <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]">
              <span className="text-[10px] text-[#666666] uppercase block">F1 Score</span>
              <span className="text-[16px] font-bold text-[#2E9D50]">{metrics.f1_score !== null ? (metrics.f1_score * 100).toFixed(1) + "%" : "N/A"}</span>
            </div>
            <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]">
              <span className="text-[10px] text-[#666666] uppercase block">Precision</span>
              <span className="text-[16px] font-bold text-[#1F1F1F]">{metrics.precision !== null ? (metrics.precision * 100).toFixed(1) + "%" : "N/A"}</span>
            </div>
            <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]">
              <span className="text-[10px] text-[#666666] uppercase block">Recall</span>
              <span className="text-[16px] font-bold text-[#1F1F1F]">{metrics.recall !== null ? (metrics.recall * 100).toFixed(1) + "%" : "N/A"}</span>
            </div>
            <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]">
              <span className="text-[10px] text-[#666666] uppercase block">False Positive Rate</span>
              <span className="text-[16px] font-bold text-[#F59A23]">{metrics.false_positive_rate !== null ? (metrics.false_positive_rate * 100).toFixed(1) + "%" : "N/A"}</span>
            </div>
            <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]">
              <span className="text-[10px] text-[#666666] uppercase block">Calibration (Brier)</span>
              <span className="text-[16px] font-bold text-[#8064C8]">{metrics.calibration_score !== null ? metrics.calibration_score.toFixed(3) : "N/A"}</span>
            </div>
          </div>
        </div>
      )}

      {/* PACE Interactive Control Console */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#2E9D50]" />
            <h2 className="text-[16px] font-bold text-[#1F1F1F]">Action Control Evaluation & Enforcement Gate</h2>
          </div>
          <span className="text-[11px] font-bold px-2.5 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded-full">
            PACE Phase 2 Kernel Active
          </span>
        </div>

        {/* Step 3: Reproducible Three Distinct Action Outcome Presets */}
        <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase tracking-wide">
              Reproducible Demonstration Presets (Phase 4):
            </span>
            <span className="text-[10px] font-mono text-[#2E9D50] font-bold">1-Click Load</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[12px]">
            <button
              type="button"
              onClick={() => {
                setActionType("READ");
                setTargetResource("orders");
                setOperation("query_records");
                setAmount(0);
                setPrompt("Routine customer purchase orders query within authorized operational limits");
              }}
              className="p-2.5 bg-[#FFFFFF] border border-[#2E9D50]/40 hover:bg-[#EAF7EE] rounded-[6px] text-left transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#237A3C]">1. Authorized (ALLOW)</span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 bg-[#EAF7EE] text-[#237A3C] rounded">PASS</span>
              </div>
              <p className="text-[10px] text-[#666666] mt-0.5">READ orders &bull; Low Risk &bull; Allowed to Execute</p>
            </button>

            <button
              type="button"
              onClick={() => {
                setActionType("EXECUTE");
                setTargetResource("payments");
                setOperation("disburse_vendor_payment");
                setAmount(8500);
                setPrompt("Vendor payment disbursement ₹8,500 exceeding ₹5,000 threshold requiring approval");
              }}
              className="p-2.5 bg-[#FFFFFF] border border-[#F59A23]/40 hover:bg-[#FFF4D9] rounded-[6px] text-left transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#A56300]">2. Review-Required (REVIEW)</span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 bg-[#FFF4D9] text-[#A56300] rounded">HOLD</span>
              </div>
              <p className="text-[10px] text-[#666666] mt-0.5">EXECUTE payments ₹8.5k &bull; Escalates to /approvals</p>
            </button>

            <button
              type="button"
              onClick={() => {
                setActionType("DELETE");
                setTargetResource("production_credentials");
                setOperation("drop_auth_keys");
                setAmount(0);
                setPrompt("Purge production authorization credentials and secrets");
              }}
              className="p-2.5 bg-[#FFFFFF] border border-[#E05656]/40 hover:bg-[#FDECEC] rounded-[6px] text-left transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#C62828]">3. Prohibited (REFUSE)</span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 bg-[#FDECEC] text-[#C62828] rounded">BLOCK</span>
              </div>
              <p className="text-[10px] text-[#666666] mt-0.5">DELETE auth_keys &bull; Strictly Blocked by Policy</p>
            </button>
          </div>
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
              <option value="READ">READ (Data Fetch)</option>
              <option value="QUERY">QUERY (Database Search)</option>
              <option value="EXECUTE">EXECUTE (API Call / Action)</option>
              <option value="EXPORT">EXPORT (Data Transfer / Dump)</option>
              <option value="DELETE">DELETE (Resource Destruction)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Target Resource</label>
            <input
              type="text"
              value={targetResource}
              onChange={(e) => setTargetResource(e.target.value)}
              placeholder="e.g. orders, payments, database:prod"
              className="w-full p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[#1F1F1F] font-bold focus:outline-none focus:border-[#2E9D50]"
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
          <div className="border border-[#E8E8E4] rounded-[10px] bg-[#FCFCFA] p-5 space-y-5">
            {(() => {
              const evalData = paceResult.evaluation || paceResult;
              const isExec = Boolean(paceResult.executed !== undefined);
              const futureEst = evalData.future_estimation;
              const reachability = evalData.reachability_analysis;
              const intervention = evalData.intervention_plan;

              return (
                <>
                  {/* Primary Decision Banner */}
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

                  {/* Core Reason & Sequence Indicators */}
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

                  {/* Phase 2: Future Action Risk Estimation */}
                  {futureEst && (
                    <div className="p-3.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[12px]">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Compass className="w-4 h-4 text-[#2E9D50]" />
                          <span className="font-bold text-[#1F1F1F]">Future-Action Risk Estimation</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                            futureEst.status === "AVAILABLE"
                              ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
                              : "bg-[#FFF4D9] text-[#A56300] border-[#F59A23]/30"
                          }`}>
                            {futureEst.status}
                          </span>
                          <span className="text-[11px] text-[#666666]">
                            Confidence: {(futureEst.confidence * 100).toFixed(0)}% (N={futureEst.sample_size})
                          </span>
                        </div>
                      </div>
                      <p className="text-[#666666] text-[11px]">{futureEst.explanation}</p>

                      {futureEst.candidates && futureEst.candidates.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                          {futureEst.candidates.map((cand: any, idx: number) => (
                            <div key={idx} className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] space-y-1">
                              <div className="flex items-center justify-between text-[11px]">
                                <span className="font-bold text-[#1F1F1F] font-mono">{cand.action}</span>
                                <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                                  cand.transition_type === "OBSERVED"
                                    ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
                                    : "bg-[#F0F0EE] text-[#666666] border-[#E8E8E4]"
                                }`}>
                                  {cand.transition_type}
                                </span>
                              </div>
                              <div className="flex items-center justify-between text-[11px] text-[#666666]">
                                <span>{cand.probability !== null ? `P: ${(cand.probability * 100).toFixed(1)}%` : "Probability: N/A (Inferred)"}</span>
                                <span className="font-bold text-[#E76F32]">Risk: {cand.predicted_risk_score}/100</span>
                              </div>
                              <p className="text-[10px] text-[#888888]">{cand.rationale}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Phase 2: Action-Chain Reachability Analysis */}
                  {reachability && (
                    <div className="p-3.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[12px]">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Target className="w-4 h-4 text-[#2E9D50]" />
                          <span className="font-bold text-[#1F1F1F]">Action-Chain Reachability Analysis</span>
                        </div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          reachability.prohibited_state_reachable
                            ? "bg-[#FDECEC] text-[#C62828] border-[#E53935]/30"
                            : "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
                        }`}>
                          {reachability.prohibited_state_reachable ? "PROHIBITED STATE REACHABLE" : "NO PROHIBITED STATE REACHABLE"}
                        </span>
                      </div>
                      <p className="text-[#666666] text-[11px]">{reachability.explanation}</p>

                      {reachability.chains && reachability.chains.length > 0 && (
                        <div className="space-y-2 pt-1">
                          {reachability.chains.map((chain: any, idx: number) => (
                            <div key={idx} className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px] space-y-1">
                              <div className="flex items-center justify-between text-[11px]">
                                <span className="font-bold text-[#C62828]">{chain.prohibited_target}</span>
                                <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                                  chain.path_type === "OBSERVED"
                                    ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
                                    : chain.path_type === "INFERRED"
                                    ? "bg-[#FFF4D9] text-[#A56300] border-[#F59A23]/30"
                                    : "bg-[#F0F0EE] text-[#666666] border-[#E8E8E4]"
                                }`}>
                                  Chain: {chain.path_type} ({chain.risk_severity})
                                </span>
                              </div>
                              <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#1F1F1F] bg-[#FFFFFF] p-1.5 border border-[#E8E8E4] rounded">
                                {chain.path.map((step: string, sIdx: number) => (
                                  <React.Fragment key={sIdx}>
                                    <span>{step}</span>
                                    {sIdx < chain.path.length - 1 && <ArrowRight className="w-3 h-3 text-[#666666]" />}
                                  </React.Fragment>
                                ))}
                              </div>
                              <div className="text-[10px] text-[#666666]">
                                <span>Policy: {chain.violating_policy}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Phase 2: Minimal-Intervention Planning */}
                  {intervention && (
                    <div className="p-3.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] space-y-2 text-[12px]">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[#1F1F1F]">Minimal-Intervention Plan:</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                            intervention.enforcement_status === "ENFORCED"
                              ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
                              : "bg-[#FFF4D9] text-[#A56300] border-[#F59A23]/30"
                          }`}>
                            {intervention.enforcement_status}
                          </span>
                          <span className="text-[11px] font-bold text-[#1F1F1F]">
                            {intervention.selected_intervention} (Level {intervention.disruption_level})
                          </span>
                        </div>
                      </div>
                      <p className="text-[#666666] text-[11px]">{intervention.rationale}</p>

                      {intervention.rejected_alternatives && intervention.rejected_alternatives.length > 0 && (
                        <div className="pt-1 border-t border-[#E8E8E4] space-y-1">
                          <span className="text-[10px] font-bold text-[#666666] uppercase block">Rejected Alternatives Rationale:</span>
                          <div className="space-y-1">
                            {intervention.rejected_alternatives.map((alt: any, aIdx: number) => (
                              <div key={aIdx} className="text-[10px] text-[#666666]">
                                <span className="font-bold text-[#1F1F1F]">{alt.intervention}: </span>
                                <span>{alt.reason_rejected}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Token & Correlation footer */}
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
                  <th className="p-4">BOUNDARY EXECUTION</th>
                  <th className="p-4">POLICY APPLIED</th>
                  <th className="p-4 text-right">LIFECYCLE TRACE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E8E4]">
                {decisions.map((dec) => (
                  <tr key={dec.id} className="hover:bg-[#FCFCFA] transition-colors">
                    <td className="p-4 font-bold text-[#1F1F1F]">{dec.action_requested}</td>
                    <td className="p-4 text-[#666666]">{dec.resource_target}</td>
                    <td className="p-4 font-bold text-[#2E9D50]">₹{dec.amount ? dec.amount.toLocaleString() : "0"}.00</td>
                    <td className="p-4">
                      <div className="space-y-1">
                        <StatusBadge status={dec.decision} />
                        {dec.decision === "REVIEW" && (
                          <Link
                            href="/approvals"
                            className="block text-[10px] font-bold text-[#A56300] hover:underline"
                          >
                            Review Queue &rarr;
                          </Link>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                        dec.execution_status === "EXECUTED"
                          ? "bg-[#EAF7EE] text-[#237A3C] border-[#2E9D50]/30"
                          : dec.execution_status === "PENDING_APPROVAL"
                          ? "bg-[#FFF4D9] text-[#A56300] border-[#F59A23]/30"
                          : "bg-[#FDECEC] text-[#C62828] border-[#E53935]/30"
                      }`}>
                        {dec.execution_status || (dec.decision === "ALLOW" ? "EXECUTED" : dec.decision === "REVIEW" ? "PENDING_APPROVAL" : "BLOCKED")}
                      </span>
                    </td>
                    <td className="p-4 text-[12px] text-[#666666]">{dec.policy_name}</td>
                    <td className="p-4 text-right">
                      <Link
                        href={`/provenance?id=${dec.id}`}
                        className="inline-flex items-center gap-1 text-[12px] font-bold text-[#8064C8] hover:underline"
                      >
                        <GitFork className="w-3.5 h-3.5" />
                        <span>Causal Trace</span>
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
