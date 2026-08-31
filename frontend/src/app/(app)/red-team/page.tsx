"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Flame, Play, ShieldCheck } from "lucide-react";

export default function RedTeamPage() {
  const [tests, setTests] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [agentId, setAgentId] = useState("");
  const [attackType, setAttackType] = useState("PROMPT_INJECTION");
  const [running, setRunning] = useState(false);

  const loadData = async () => {
    try {
      const [tData, aData] = await Promise.all([
        fetchApi("/red-team/tests").catch(() => []),
        fetchApi("/agents").catch(() => []),
      ]);
      setTests(tData || []);
      setAgents(aData || []);
      if (aData && aData.length > 0) setAgentId(aData[0].id);
    } catch (err) {
      console.error("Red-team fetch error:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunAttack = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    try {
      await fetchApi("/red-team/run", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, attack_type: attackType }),
      });
      await loadData();
    } catch (err: any) {
      alert(`Attack run error: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Red-Team Simulation Lab</h1>
        <p className="text-[13px] text-[#666666]">
          Adversarial Vulnerability Simulation & Defense Verification
        </p>
      </div>

      {/* Simulation Launcher Card */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm">
        <h2 className="text-[16px] font-bold text-[#1F1F1F] flex items-center gap-2">
          <Flame className="w-4 h-4 text-[#E53935]" />
          <span>Execute Adversarial Simulation Vector</span>
        </h2>

        <form onSubmit={handleRunAttack} className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Attack Vector</label>
            <select
              value={attackType}
              onChange={(e) => setAttackType(e.target.value)}
              className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
            >
              <option value="PROMPT_INJECTION">Prompt Injection & Guardrail Bypass</option>
              <option value="GOAL_HIJACKING">Goal Hijacking & Action Splitting</option>
              <option value="PRIVILEGE_ESCALATION">Privilege Escalation & SQL Injection</option>
              <option value="TOOL_ABUSE">Tool Abuse & Unauthorized S3 Bucket Delete</option>
              <option value="DATA_EXFILTRATION">Mass Data Exfiltration Vector</option>
            </select>
          </div>

          <div className="md:col-span-2 flex items-end">
            <button
              type="submit"
              disabled={running || agents.length === 0}
              className="w-full py-2 bg-[#E53935] hover:bg-[#C62828] text-white rounded-[6px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              <span>{running ? "Simulating Attack..." : "Launch Adversarial Attack Test"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Test Log Table */}
      {tests.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Flame className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Security Simulations Executed</h3>
          <p className="text-[12px] text-[#666666]">
            No red-team simulation records exist in the database. Use the launcher above to test agent defenses.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">TEST TYPE</th>
                <th className="p-4">PAYLOAD</th>
                <th className="p-4">DEFENSE OUTCOME</th>
                <th className="p-4">SECURITY SCORE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {tests.map((t) => (
                <tr key={t.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-bold text-[#1F1F1F]">{t.test_type}</td>
                  <td className="p-4 font-mono text-[11px] text-[#666666] max-w-xs truncate">{t.attack_payload}</td>
                  <td className="p-4"><StatusBadge status={t.defense_result} /></td>
                  <td className="p-4 font-bold text-[#2E9D50]">{t.security_score} / 100</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
