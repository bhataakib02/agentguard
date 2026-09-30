"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Flame, Play, ShieldCheck, AlertTriangle, Info, CheckCircle2, XCircle } from "lucide-react";

export default function RedTeamPage() {
  const [tests, setTests] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [agentId, setAgentId] = useState("");
  const [attackType, setAttackType] = useState("AUTHORIZATION_BOUNDARY");
  const [running, setRunning] = useState(false);
  const [latestResult, setLatestResult] = useState<any>(null);

  const loadData = async () => {
    try {
      const [tData, aData] = await Promise.all([
        fetchApi("/red-team/tests").catch(() => []),
        fetchApi("/agents").catch(() => []),
      ]);
      setTests(tData || []);
      setAgents(aData || []);
      if (aData && aData.length > 0 && !agentId) setAgentId(aData[0].id);
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
    setLatestResult(null);
    try {
      const res = await fetchApi("/red-team/run", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, attack_type: attackType }),
      });
      setLatestResult(res);
      await loadData();
    } catch (err: any) {
      alert(`Attack run error: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[#E8E8E4] pb-5">
        <div className="flex items-center gap-3">
          <h1 className="text-[24px] font-bold text-[#1F1F1F]">Red-Team Governance & Security Lab</h1>
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#EAF7EE] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
            REAL POLICY EVALUATIONS
          </span>
        </div>
        <p className="text-[13px] text-[#666666] mt-1">
          Controlled Policy Boundary Verification & Adversarial Stress Testing Against Policy Engine
        </p>
      </div>

      {/* Safety & Lab Notice Banner */}
      <div className="bg-[#FFFDF5] border border-[#F59A23]/30 rounded-[12px] p-4 flex items-start gap-3 text-[12px] text-[#666666]">
        <Info className="w-5 h-5 text-[#F59A23] shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-[#1F1F1F] block">Internal Governance Safety Notice</span>
          This lab evaluates your agent&apos;s real database-backed policies against controlled synthetic attack vectors.
          All tests run in an isolated simulation context and do NOT execute real external attacks, destructive actions, or arbitrary network exploits.
        </div>
      </div>

      {/* Simulation Launcher Card */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm">
        <h2 className="text-[16px] font-bold text-[#1F1F1F] flex items-center gap-2">
          <Flame className="w-4 h-4 text-[#E53935]" />
          <span>Launch Controlled Adversarial Scenario</span>
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
            <label className="block text-[11px] font-bold text-[#666666] uppercase mb-1">Scenario Vector</label>
            <select
              value={attackType}
              onChange={(e) => setAttackType(e.target.value)}
              className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
            >
              <option value="AUTHORIZATION_BOUNDARY">[REAL] Authorization Boundary & Root Escalation</option>
              <option value="FINANCIAL_CAP_EXCESS">[REAL] Autonomous Financial Ceiling Abuse (₹1,50,000)</option>
              <option value="UNSAFE_DELETION">[REAL] Unsafe Production Table Deletion</option>
              <option value="POLICY_BYPASS_ATTEMPT">[REAL] Mid-Tier Financial Bypass (₹7,500)</option>
              <option value="TOOL_ABUSE">[REAL] Cloud Bucket Deletion Tool Abuse</option>
              <option value="PROMPT_INJECTION">[SIMULATED] System Prompt Injection & Context Exfiltration</option>
            </select>
          </div>

          <div className="md:col-span-2 flex items-end">
            <button
              type="submit"
              disabled={running || agents.length === 0}
              className="w-full py-2 bg-[#E53935] hover:bg-[#C62828] text-white rounded-[6px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              <span>{running ? "Evaluating Policy Defenses..." : "Launch Governance Test"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Latest Result Inspection Card */}
      {latestResult && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
            <div className="flex items-center gap-2">
              {latestResult.test?.defense_result === "PASSED" ? (
                <CheckCircle2 className="w-5 h-5 text-[#2E9D50]" />
              ) : (
                <XCircle className="w-5 h-5 text-[#E53935]" />
              )}
              <h3 className="font-bold text-[15px] text-[#1F1F1F]">
                Test Evaluation: {latestResult.test?.test_type}
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#FCFCFA] border border-[#E8E8E4] text-[#666666] font-mono">
              {latestResult.test_category}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-[12px]">
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Defense Result</span>
              <span className={`text-[18px] font-bold ${latestResult.test?.defense_result === "PASSED" ? "text-[#2E9D50]" : "text-[#E53935]"}`}>
                {latestResult.test?.defense_result}
              </span>
            </div>
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Policy Decision</span>
              <span className="text-[18px] font-bold text-[#1F1F1F]">
                {latestResult.actual_outcome} (Expected: {latestResult.expected_outcome})
              </span>
            </div>
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Enforcing Policy</span>
              <span className="text-[14px] font-bold text-[#8064C8] truncate block">
                {latestResult.policy_applied}
              </span>
            </div>
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[#666666] block font-mono text-[10px] uppercase">Security Score</span>
              <span className="text-[18px] font-bold text-[#2E9D50]">
                {latestResult.test?.security_score} / 100
              </span>
            </div>
          </div>

          <p className="text-[12px] text-[#666666] bg-[#FCFCFA] p-3 rounded-[8px] border border-[#E8E8E4]">
            <strong>Mitigation Detail:</strong> {latestResult.mitigation_detail}
          </p>
        </div>
      )}

      {/* Test Log Table */}
      {tests.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Flame className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Security Evaluations Executed</h3>
          <p className="text-[12px] text-[#666666]">
            No test records exist in the database. Use the launcher above to test agent defenses against active policies.
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
