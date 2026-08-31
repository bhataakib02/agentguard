"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Zap, Plus, Flame } from "lucide-react";

export default function CapabilitiesPage() {
  const [tokens, setTokens] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Issue Token Form
  const [agentId, setAgentId] = useState("");
  const [capabilityName, setCapabilityName] = useState("refund:create");
  const [scope, setScope] = useState("customer=9281");
  const [amountLimit, setAmountLimit] = useState(5000);
  const [issuing, setIssuing] = useState(false);

  const loadTokens = async () => {
    try {
      setLoading(true);
      const [tokData, agData] = await Promise.all([
        fetchApi("/capabilities").catch(() => []),
        fetchApi("/agents").catch(() => []),
      ]);
      setTokens(tokData || []);
      setAgents(agData || []);
      if (agData && agData.length > 0) setAgentId(agData[0].id);
    } catch (err) {
      console.error("Capabilities fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTokens();
  }, []);

  const handleIssueToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setIssuing(true);
    try {
      await fetchApi("/capabilities/issue", {
        method: "POST",
        body: JSON.stringify({
          agent_id: agentId,
          capability_name: capabilityName,
          scope,
          amount_limit: Number(amountLimit),
          ttl_seconds: 300,
        }),
      });
      await loadTokens();
    } catch (err: any) {
      alert(`Issue error: ${err.message}`);
    } finally {
      setIssuing(false);
    }
  };

  const handleRevoke = async (tokenCode: string) => {
    try {
      await fetchApi(`/capabilities/revoke/${tokenCode}`, { method: "POST" });
      await loadTokens();
    } catch (err: any) {
      alert(`Revoke error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Dynamic Capability Tokens</h1>
        <p className="text-[13px] text-[#666666]">
          Short-Lived, Task-Specific Cryptographic Authority Tokens
        </p>
      </div>

      {/* Issue Token Form Card */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm">
        <h2 className="text-[16px] font-bold text-[#1F1F1F] flex items-center gap-2">
          <Zap className="w-4 h-4 text-[#2E9D50]" />
          <span>Issue Dynamic Capability Token</span>
        </h2>

        <form onSubmit={handleIssueToken} className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div>
            <label className="block text-[11px] font-bold text-[#666666] mb-1 uppercase">Select Agent</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full px-3 py-2 text-[12px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
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
            <label className="block text-[11px] font-bold text-[#666666] mb-1 uppercase">Capability</label>
            <input
              type="text"
              required
              value={capabilityName}
              onChange={(e) => setCapabilityName(e.target.value)}
              placeholder="refund:create"
              className="w-full px-3 py-2 text-[12px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#666666] mb-1 uppercase">Scope</label>
            <input
              type="text"
              required
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              placeholder="customer=9281"
              className="w-full px-3 py-2 text-[12px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#666666] mb-1 uppercase">Cap Limit (₹)</label>
            <input
              type="number"
              required
              value={amountLimit}
              onChange={(e) => setAmountLimit(Number(e.target.value))}
              className="w-full px-3 py-2 text-[12px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={issuing || agents.length === 0}
              className="w-full py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[6px] text-[12px] font-bold transition-colors disabled:opacity-50"
            >
              {issuing ? "Issuing..." : "Issue Token"}
            </button>
          </div>
        </form>
      </div>

      {/* Capability Token List Table */}
      {tokens.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Zap className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Capability Tokens Issued</h3>
          <p className="text-[12px] text-[#666666]">
            No capability tokens currently exist in the database. Use the issuer above to generate tokens.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[11px] font-bold text-[#666666] uppercase">
                <th className="p-4">TOKEN CODE</th>
                <th className="p-4">CAPABILITY</th>
                <th className="p-4">SCOPE</th>
                <th className="p-4">LIMIT</th>
                <th className="p-4">STATUS</th>
                <th className="p-4 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {tokens.map((tok) => (
                <tr key={tok.id} className="hover:bg-[#FCFCFA] transition-colors">
                  <td className="p-4 font-mono text-[12px] text-[#8064C8] font-bold">{tok.token_code}</td>
                  <td className="p-4 font-bold text-[#1F1F1F]">{tok.capability_name}</td>
                  <td className="p-4 text-[#666666]">{tok.scope}</td>
                  <td className="p-4 font-bold text-[#2E9D50]">₹{tok.amount_limit ? tok.amount_limit.toLocaleString() : "0"}</td>
                  <td className="p-4"><StatusBadge status={tok.status} /></td>
                  <td className="p-4 text-right">
                    {tok.status === "ACTIVE" && (
                      <button
                        onClick={() => handleRevoke(tok.token_code)}
                        className="px-3 py-1 bg-[#FDECEC] text-[#C62828] border border-[#E53935]/30 rounded-[6px] text-[11px] font-bold hover:bg-[#F9D4D4]"
                      >
                        Revoke Token
                      </button>
                    )}
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
