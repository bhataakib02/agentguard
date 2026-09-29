"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import {
  Activity,
  RefreshCw,
  Cpu,
  Wallet,
  AlertTriangle,
  ArrowRight,
  Flame,
  ShieldAlert,
  TrendingUp,
  Zap,
  DollarSign,
  BarChart3,
  Clock,
} from "lucide-react";
import StatusBadge from "@/components/ui/StatusBadge";

export default function TelemetryDashboardPage() {
  const [tokenUsage, setTokenUsage] = useState<any>(null);
  const [costByAgent, setCostByAgent] = useState<any[]>([]);
  const [riskSignals, setRiskSignals] = useState<any[]>([]);
  const [circuitBreakers, setCircuitBreakers] = useState<any[]>([]);
  const [budgets, setBudgets] = useState<any[]>([]);
  const [webhookHealth, setWebhookHealth] = useState<any>(null);
  const [executions, setExecutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState("30d");

  const loadTelemetry = async () => {
    setLoading(true);
    try {
      const [tok, agents, signals, cbs, budg, wh, execs] = await Promise.all([
        fetchApi(`/telemetry/token-usage?range=${range}`).catch(() => null),
        fetchApi(`/telemetry/cost-by-agent?range=${range}`).catch(() => ({agents: []})),
        fetchApi(`/telemetry/risk-signals?range=7d`).catch(() => ({signals: []})),
        fetchApi(`/telemetry/circuit-breakers`).catch(() => []),
        fetchApi(`/telemetry/budgets`).catch(() => []),
        fetchApi(`/telemetry/webhook-health?range=7d`).catch(() => null),
        fetchApi(`/telemetry/executions?range=24h&limit=15`).catch(() => ({executions: []})),
      ]);
      setTokenUsage(tok);
      setCostByAgent(agents?.agents || []);
      setRiskSignals(signals?.signals || []);
      setCircuitBreakers(cbs || []);
      setBudgets(budg || []);
      setWebhookHealth(wh);
      setExecutions(execs?.executions || []);
    } catch (err) {
      console.error("Telemetry load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTelemetry(); }, [range]);

  const fmtNum = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(2)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  const fmtCost = (n: number) => {
    if (n >= 1) return `$${n.toFixed(2)}`;
    if (n > 0) return `$${n.toFixed(4)}`;
    return "$0.00";
  };

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight" style={{ fontFamily: "'Times New Roman', serif" }}>
              Runtime Telemetry & Cost Governance
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#1A2744] text-[#4BA3F5] border border-[#4BA3F5]/40 font-mono">
              PHASE 4
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Real-time agent execution telemetry, token usage tracking, cost analytics, budget governance & risk signals.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {["24h", "7d", "30d", "90d"].map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1.5 rounded-[6px] text-[11px] font-bold transition-colors border ${
                range === r
                  ? "bg-[#1A2744] text-[#4BA3F5] border-[#4BA3F5]/40"
                  : "bg-[#0D1117] text-[#64748B] border-[#1E2638] hover:text-white"
              }`}
            >
              {r}
            </button>
          ))}
          <button
            onClick={loadTelemetry}
            className="ml-2 px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#4BA3F5]" : ""}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#4BA3F5]" />
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Executions</span>
          </div>
          <h2 className="text-[28px] font-bold text-white">{loading ? "—" : fmtNum(tokenUsage?.execution_count || 0)}</h2>
          <span className="text-[11px] text-[#94A3B8]">In selected range</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#A78BFA]" />
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Total Tokens</span>
          </div>
          <h2 className="text-[28px] font-bold text-white">{loading ? "—" : fmtNum(tokenUsage?.total_tokens || 0)}</h2>
          <span className="text-[11px] text-[#94A3B8]">Input: {fmtNum(tokenUsage?.input_tokens || 0)} • Output: {fmtNum(tokenUsage?.output_tokens || 0)}</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-[#2E9D50]" />
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Total Cost</span>
          </div>
          <h2 className="text-[28px] font-bold text-white">{loading ? "—" : fmtCost(tokenUsage?.total_cost || 0)}</h2>
          <span className="text-[11px] text-[#94A3B8]">Based on configured pricing</span>
        </div>
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-1">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#F59E0B]" />
            <span className="text-[10px] font-bold text-[#64748B] uppercase font-mono">Avg Latency</span>
          </div>
          <h2 className="text-[28px] font-bold text-white">{loading ? "—" : `${tokenUsage?.avg_latency_ms || 0}ms`}</h2>
          <span className="text-[11px] text-[#94A3B8]">Decision evaluation time</span>
        </div>
      </div>

      {/* Two-column: Risk Signals + Circuit Breakers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Signals */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#F59E0B]" />
              <h3 className="text-[14px] font-bold text-white">Active Risk Signals</h3>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#3D2900] text-[#F59E0B] border border-[#F59E0B]/30">
              {riskSignals.filter((s) => s.status === "ACTIVE").length} ACTIVE
            </span>
          </div>
          {riskSignals.length === 0 ? (
            <div className="text-center py-8">
              <ShieldAlert className="w-8 h-8 text-[#2E9D50] mx-auto mb-2 opacity-40" />
              <p className="text-[12px] text-[#64748B]">No active risk signals — all agents operating within normal parameters.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[250px] overflow-y-auto">
              {riskSignals.slice(0, 10).map((sig, i) => (
                <div key={sig.id || i} className="p-3 bg-[#0D1117] border border-[#1E2638] rounded-[8px]">
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] font-bold text-white">{sig.title}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                      sig.severity === "CRITICAL" ? "bg-[#3D0F0F] text-[#E53935] border border-[#E53935]/30" :
                      sig.severity === "HIGH" ? "bg-[#3D2900] text-[#F59E0B] border border-[#F59E0B]/30" :
                      "bg-[#1A2744] text-[#4BA3F5] border border-[#4BA3F5]/30"
                    }`}>{sig.severity}</span>
                  </div>
                  <p className="text-[11px] text-[#94A3B8] mt-1">{sig.description}</p>
                  <span className="text-[10px] text-[#64748B] font-mono">{sig.signal_type} • {sig.timestamp?.slice(0, 16)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Circuit Breakers */}
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-[#E53935]" />
              <h3 className="text-[14px] font-bold text-white">Circuit Breakers</h3>
            </div>
          </div>
          {circuitBreakers.length === 0 ? (
            <div className="text-center py-8">
              <Flame className="w-8 h-8 text-[#64748B] mx-auto mb-2 opacity-30" />
              <p className="text-[12px] text-[#64748B]">No circuit breakers registered.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[250px] overflow-y-auto">
              {circuitBreakers.map((cb, i) => (
                <div key={cb.agent_id || i} className="p-3 bg-[#0D1117] border border-[#1E2638] rounded-[8px] flex items-center justify-between">
                  <div>
                    <span className="text-[12px] font-bold text-white block">{cb.name}</span>
                    <span className="text-[10px] text-[#A78BFA] font-bold">{cb.agent_code}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={cb.circuit_breaker_state || cb.state} />
                    {cb.budget_state && cb.budget_state !== "UNCONFIGURED" && cb.budget_state !== "NORMAL" && (
                      <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[#3D2900] text-[#F59E0B] border border-[#F59E0B]/30">
                        BUDGET: {cb.budget_state}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Cost by Agent Table */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-4 h-4 text-[#A78BFA]" />
          <h3 className="text-[14px] font-bold text-white">Cost by Agent</h3>
        </div>
        {costByAgent.length === 0 ? (
          <div className="text-center py-8">
            <Wallet className="w-8 h-8 text-[#64748B] mx-auto mb-2 opacity-30" />
            <p className="text-[12px] text-[#64748B]">No execution data recorded yet. Evaluate decisions to generate telemetry.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="text-[10px] font-bold text-[#64748B] uppercase border-b border-[#1E2638]">
                  <th className="p-3">Agent</th>
                  <th className="p-3">Executions</th>
                  <th className="p-3">Tokens</th>
                  <th className="p-3">Cost</th>
                  <th className="p-3">Avg Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2638]">
                {costByAgent.map((agent, i) => (
                  <tr key={agent.agent_id || i} className="hover:bg-[#161C2A] transition-colors">
                    <td className="p-3">
                      <span className="font-bold text-white">{agent.agent_name}</span>
                      <span className="text-[10px] text-[#A78BFA] ml-2">{agent.agent_code}</span>
                    </td>
                    <td className="p-3 text-[#E1E7F0]">{fmtNum(agent.execution_count)}</td>
                    <td className="p-3 text-[#E1E7F0]">{fmtNum(agent.total_tokens)}</td>
                    <td className="p-3 text-[#2E9D50] font-bold">{fmtCost(agent.total_cost)}</td>
                    <td className="p-3">
                      <span className={`${agent.avg_risk_score > 60 ? "text-[#E53935]" : agent.avg_risk_score > 30 ? "text-[#F59E0B]" : "text-[#2E9D50]"}`}>
                        {agent.avg_risk_score}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Budget Governance */}
      {budgets.length > 0 && (
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5">
          <div className="flex items-center gap-2 mb-4">
            <Wallet className="w-4 h-4 text-[#2E9D50]" />
            <h3 className="text-[14px] font-bold text-white">Budget Governance</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {budgets.map((b, i) => (
              <div key={b.id || i} className="p-4 bg-[#0D1117] border border-[#1E2638] rounded-[8px] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-bold text-white">{b.agent_name || "Org Default"}</span>
                  <StatusBadge status={b.budget_state} />
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[#64748B]">Daily Tokens</span>
                    <span className="block text-white font-bold">{fmtNum(b.current_daily_tokens || 0)} / {fmtNum(b.daily_token_limit || 0)}</span>
                  </div>
                  <div>
                    <span className="text-[#64748B]">Daily Cost</span>
                    <span className="block text-white font-bold">{fmtCost(b.current_daily_cost || 0)} / {fmtCost(b.daily_cost_limit || 0)}</span>
                  </div>
                  <div>
                    <span className="text-[#64748B]">Monthly Cost</span>
                    <span className="block text-white font-bold">{fmtCost(b.current_monthly_cost || 0)} / {fmtCost(b.monthly_cost_limit || 0)}</span>
                  </div>
                  <div>
                    <span className="text-[#64748B]">Executions Today</span>
                    <span className="block text-white font-bold">{b.current_daily_executions || 0} / {b.execution_count_limit || "∞"}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Executions */}
      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-[#F59E0B]" />
            <h3 className="text-[14px] font-bold text-white">Recent Executions (24h)</h3>
          </div>
          <span className="text-[10px] text-[#64748B] font-mono">{executions.length} records</span>
        </div>
        {executions.length === 0 ? (
          <div className="text-center py-8">
            <Zap className="w-8 h-8 text-[#64748B] mx-auto mb-2 opacity-30" />
            <p className="text-[12px] text-[#64748B]">No recent execution telemetry. Evaluate decisions to generate data.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[11px]">
              <thead>
                <tr className="text-[10px] font-bold text-[#64748B] uppercase border-b border-[#1E2638]">
                  <th className="p-2">Action</th>
                  <th className="p-2">Outcome</th>
                  <th className="p-2">Risk</th>
                  <th className="p-2">Tokens</th>
                  <th className="p-2">Cost</th>
                  <th className="p-2">Latency</th>
                  <th className="p-2">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2638]">
                {executions.map((ex, i) => (
                  <tr key={ex.id || i} className="hover:bg-[#161C2A] transition-colors">
                    <td className="p-2 text-white font-medium">{ex.action || "—"}</td>
                    <td className="p-2"><StatusBadge status={ex.policy_decision || ex.outcome} /></td>
                    <td className="p-2">
                      <span className={`font-bold ${ex.risk_score > 60 ? "text-[#E53935]" : ex.risk_score > 30 ? "text-[#F59E0B]" : "text-[#2E9D50]"}`}>
                        {ex.risk_score}
                      </span>
                    </td>
                    <td className="p-2 text-[#E1E7F0]">{fmtNum(ex.total_tokens || 0)}</td>
                    <td className="p-2 text-[#2E9D50]">{fmtCost(ex.estimated_cost || 0)}</td>
                    <td className="p-2 text-[#E1E7F0]">{ex.latency_ms || 0}ms</td>
                    <td className="p-2 text-[#64748B] font-mono text-[10px]">{ex.timestamp?.slice(11, 19) || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Webhook Delivery Health */}
      {webhookHealth && (
        <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4 text-[#4BA3F5]" />
            <h3 className="text-[14px] font-bold text-white">Webhook Delivery Health</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <span className="text-[28px] font-bold text-white">{webhookHealth.successful || 0}</span>
              <span className="block text-[10px] text-[#2E9D50] font-bold uppercase">Delivered</span>
            </div>
            <div>
              <span className="text-[28px] font-bold text-white">{webhookHealth.failed || 0}</span>
              <span className="block text-[10px] text-[#E53935] font-bold uppercase">Failed</span>
            </div>
            <div>
              <span className="text-[28px] font-bold text-white">{webhookHealth.dead_letter || 0}</span>
              <span className="block text-[10px] text-[#F59E0B] font-bold uppercase">Dead Letter</span>
            </div>
            <div>
              <span className="text-[28px] font-bold text-white">{webhookHealth.success_rate || 0}%</span>
              <span className="block text-[10px] text-[#4BA3F5] font-bold uppercase">Success Rate</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
