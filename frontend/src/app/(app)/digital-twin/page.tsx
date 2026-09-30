"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Cpu, Play, AlertCircle, Info, CheckCircle2 } from "lucide-react";

export default function DigitalTwinPage() {
  const [sims, setSims] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [agentId, setAgentId] = useState("");
  const [scenario, setScenario] = useState("TRAFFIC_SPIKE");
  const [running, setRunning] = useState(false);
  const [latestResult, setLatestResult] = useState<any>(null);

  const loadData = async () => {
    try {
      const [sData, aData] = await Promise.all([
        fetchApi("/digital-twin/simulations").catch(() => []),
        fetchApi("/agents").catch(() => []),
      ]);
      setSims(sData || []);
      setAgents(aData || []);
      if (aData && aData.length > 0 && !agentId) setAgentId(aData[0].id);
    } catch (err) {
      console.error("Digital twin fetch error:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunSim = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setLatestResult(null);
    try {
      const res = await fetchApi("/digital-twin/run", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, scenario_type: scenario }),
      });
      setLatestResult(res);
      await loadData();
    } catch (err: any) {
      alert(`Simulation error: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[#E8E8E4] pb-5">
        <div className="flex items-center gap-3">
          <h1 className="text-[24px] font-bold text-[#1F1F1F]">Agent Digital Twin Simulator</h1>
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#EAE8F8] text-[#8064C8] border border-[#8064C8]/30 font-mono">
            SIMULATED
          </span>
        </div>
        <p className="text-[13px] text-[#666666] mt-1">
          Deterministic Sandboxed Stress Testing & Scenario Heuristic Analysis
        </p>
      </div>

      {/* Simulation Truthfulness Disclaimer Banner */}
      <div className="bg-[#FFFDF5] border border-[#F59A23]/30 rounded-[12px] p-4 flex items-start gap-3 text-[12px] text-[#666666]">
        <Info className="w-5 h-5 text-[#F59A23] shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-[#1F1F1F] block">Deterministic Simulation Notice</span>
          Outputs are hypothetical stress projections computed from actual historical execution telemetry,
          budget configurations, and active policy counts. This simulator does not claim or use machine-learning
          prediction models, and does not represent actual future behavior.
        </div>
      </div>

      {/* Launcher Card */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm">
        <h2 className="text-[16px] font-bold text-[#1F1F1F] flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[#8064C8]" />
          <span>Launch Sandboxed Digital Twin Stress Test</span>
        </h2>

        <form onSubmit={handleRunSim} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Target Agent</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
            >
              {agents.length === 0 ? (
                <option value="">No agents available</option>
              ) : (
                agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.agent_code} ({a.name})
                  </option>
                ))
              )}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Scenario Type</label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
            >
              <option value="TRAFFIC_SPIKE">High Volume Traffic Spike (50k reqs)</option>
              <option value="API_FAILURE">Upstream Payment API Failure Rate</option>
              <option value="MALICIOUS_INPUT">Adversarial Input & Policy Resistance</option>
            </select>
          </div>

          <div className="md:col-span-2 flex items-end">
            <button
              type="submit"
              disabled={running || agents.length === 0}
              className="w-full py-2 bg-[#8064C8] hover:bg-[#684DAE] text-white rounded-[6px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              <span>{running ? "Simulating Twin..." : "Run Digital Twin Stress Test"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Latest Result Inspection Card */}
      {latestResult && (
        <div className="bg-[#FFFFFF] border border-[#8064C8]/30 rounded-[12px] p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#8064C8]" />
              <h3 className="font-bold text-[15px] text-[#1F1F1F]">
                Stress Test Result: {latestResult.scenario_type}
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#EAE8F8] text-[#8064C8] font-mono">
              SIMULATED HYPOTHETICAL
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-[12px]">
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Readiness Score</span>
              <span className="text-[20px] font-bold text-[#8064C8]">{latestResult.readiness_score} / 100</span>
            </div>
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Projected Latency P99</span>
              <span className="text-[20px] font-bold text-[#1F1F1F]">{latestResult.metrics?.latency_p99 || "N/A"}</span>
            </div>
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Projected Error Rate</span>
              <span className="text-[20px] font-bold text-[#F59A23]">{latestResult.metrics?.error_rate || "N/A"}</span>
            </div>
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Observed Real Executions</span>
              <span className="text-[20px] font-bold text-[#1F1F1F]">
                {latestResult.inputs_real?.historical_executions_observed ?? 0}
              </span>
            </div>
          </div>

          <p className="text-[12px] text-[#666666] bg-[#FCFCFA] p-3 rounded-[8px] border border-[#E8E8E4]">
            <strong>Recommendation:</strong> {latestResult.deployment_recommendation}
          </p>
        </div>
      )}

      {/* Simulation Log Table */}
      {sims.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Cpu className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Digital Twin Simulations Executed</h3>
          <p className="text-[12px] text-[#666666]">
            No simulation logs exist in the database. Run a simulation to inspect deterministic pre-production metrics.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">SCENARIO TYPE</th>
                <th className="p-4">CLASSIFICATION</th>
                <th className="p-4">READINESS SCORE</th>
                <th className="p-4">PROJECTED LATENCY</th>
                <th className="p-4">THROUGHPUT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {sims.map((s) => (
                <tr key={s.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-bold text-[#1F1F1F]">{s.scenario_type}</td>
                  <td className="p-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#EAE8F8] text-[#8064C8] font-mono">
                      SIMULATED
                    </span>
                  </td>
                  <td className="p-4 font-bold text-[#2E9D50]">{s.readiness_score} / 100</td>
                  <td className="p-4 text-[#666666]">
                    {s.metrics_json?.metrics?.latency_p99 || s.metrics_json?.latency_p99 || "N/A"}
                  </td>
                  <td className="p-4 text-[#666666]">
                    {s.metrics_json?.metrics?.throughput || s.metrics_json?.throughput || "N/A"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
