"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Cpu, Play } from "lucide-react";

export default function DigitalTwinPage() {
  const [sims, setSims] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [agentId, setAgentId] = useState("");
  const [scenario, setScenario] = useState("TRAFFIC_SPIKE");
  const [running, setRunning] = useState(false);

  const loadData = async () => {
    try {
      const [sData, aData] = await Promise.all([
        fetchApi("/digital-twin/simulations").catch(() => []),
        fetchApi("/agents").catch(() => []),
      ]);
      setSims(sData || []);
      setAgents(aData || []);
      if (aData && aData.length > 0) setAgentId(aData[0].id);
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
    try {
      await fetchApi("/digital-twin/run", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, scenario_type: scenario }),
      });
      await loadData();
    } catch (err: any) {
      alert(`Simulation error: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Agent Digital Twin Simulator</h1>
        <p className="text-[13px] text-[#666666]">
          Pre-Production Sandboxed Simulation & Behavioral Stress Testing
        </p>
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
              <option value="MALICIOUS_INPUT">High Volume Malicious Inputs</option>
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

      {/* Simulation Log Table */}
      {sims.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Cpu className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Digital Twin Simulations Executed</h3>
          <p className="text-[12px] text-[#666666]">
            No simulation logs exist in the database. Run a simulation to inspect pre-production metrics.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">SCENARIO TYPE</th>
                <th className="p-4">READINESS SCORE</th>
                <th className="p-4">THROUGHPUT</th>
                <th className="p-4">LATENCY P99</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {sims.map((s) => (
                <tr key={s.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-bold text-[#1F1F1F]">{s.scenario_type}</td>
                  <td className="p-4 font-bold text-[#2E9D50]">{s.readiness_score} / 100</td>
                  <td className="p-4 text-[#666666]">{s.metrics_json?.throughput || "N/A"}</td>
                  <td className="p-4 text-[#666666]">{s.metrics_json?.latency_p99 || "N/A"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
