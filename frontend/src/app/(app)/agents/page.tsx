"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Bot, Plus, ArrowRight, ShieldCheck, Flame } from "lucide-react";

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [department, setDepartment] = useState("Operations");
  const [purpose, setPurpose] = useState("");
  const [autonomyLevel, setAutonomyLevel] = useState("MEDIUM");
  const [dailyBudget, setDailyBudget] = useState(10000);
  const [submitting, setSubmitting] = useState(false);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const data = await fetchApi("/agents");
      setAgents(data || []);
    } catch (err) {
      console.error("Agents fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await fetchApi("/agents", {
        method: "POST",
        body: JSON.stringify({
          name,
          department,
          purpose,
          autonomy_level: autonomyLevel,
          daily_budget: Number(dailyBudget),
        }),
      });
      setShowModal(false);
      setName("");
      setPurpose("");
      await loadAgents();
    } catch (err: any) {
      alert(`Error creating agent: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleKillSwitch = async (agentId: string, currentStatus: string) => {
    try {
      const endpoint = currentStatus === "SUSPENDED" ? `/agents/${agentId}/restore` : `/agents/${agentId}/suspend`;
      await fetchApi(endpoint, { method: "POST" });
      await loadAgents();
    } catch (err: any) {
      alert(`Kill switch error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-5">
        <div>
          <h1 className="text-[24px] font-bold text-[#1F1F1F]">AI Employee Directory</h1>
          <p className="text-[13px] text-[#666666]">
            Registered Autonomous AI Agents, Passports, & Operational Status
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center gap-2 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Register New AI Agent</span>
        </button>
      </div>

      {agents.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-4">
          <Bot className="w-12 h-12 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[18px] font-bold text-[#1F1F1F]">Zero AI Agents Registered</h3>
          <p className="text-[13px] text-[#666666] max-w-md mx-auto">
            Your database currently contains zero registered AI employees. Register an autonomous agent to start monitoring and enforcing zero-trust policies.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="px-5 py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold shadow-sm"
          >
            Create First AI Agent
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-4 shadow-sm hover:border-[#2E9D50] transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#EAF7EE] flex items-center justify-center text-[#2E9D50] border border-[#2E9D50]/30">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-[15px] font-bold text-[#1F1F1F]">{agent.name}</h3>
                    <span className="text-[11px] font-bold text-[#8064C8]">{agent.agent_code} • {agent.department}</span>
                  </div>
                </div>
                <StatusBadge status={agent.status} />
              </div>

              <p className="text-[12px] text-[#666666] line-clamp-2">{agent.purpose}</p>

              <div className="grid grid-cols-2 gap-2 text-[11px] p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                <div>
                  <span className="text-[#666666] block uppercase text-[10px] font-bold">AUTONOMY</span>
                  <strong className="text-[#1F1F1F]">{agent.autonomy_level}</strong>
                </div>
                <div>
                  <span className="text-[#666666] block uppercase text-[10px] font-bold">RISK SCORE</span>
                  <strong className={agent.risk_score > 50 ? "text-[#E53935]" : "text-[#2E9D50]"}>
                    {agent.risk_score} / 100
                  </strong>
                </div>
                <div>
                  <span className="text-[#666666] block uppercase text-[10px] font-bold">MODEL</span>
                  <strong className="text-[#8064C8]">{agent.model_name}</strong>
                </div>
                <div>
                  <span className="text-[#666666] block uppercase text-[10px] font-bold">DAILY BUDGET</span>
                  <strong className="text-[#2E9D50]">₹{agent.daily_budget ? agent.daily_budget.toLocaleString() : "0"}</strong>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[#E8E8E4]">
                <Link
                  href={`/agents/passport?id=${agent.id}`}
                  className="text-[12px] font-bold text-[#2878D4] hover:underline flex items-center gap-1"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Passport</span>
                </Link>

                <button
                  onClick={() => handleKillSwitch(agent.id, agent.status)}
                  className={`px-3 py-1 rounded-[6px] text-[11px] font-bold flex items-center gap-1 transition-colors ${
                    agent.status === "SUSPENDED"
                      ? "bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30"
                      : "bg-[#FDECEC] text-[#C62828] border border-[#E53935]/30"
                  }`}
                >
                  <Flame className="w-3 h-3" />
                  <span>{agent.status === "SUSPENDED" ? "Restore Agent" : "Kill Switch"}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for Creating New AI Agent */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] max-w-lg w-full p-6 space-y-5 shadow-xl">
            <h2 className="text-[20px] font-bold text-[#1F1F1F]">Register New AI Employee</h2>

            <form onSubmit={handleCreateAgent} className="space-y-4">
              <div>
                <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">Agent Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="BillingAssistantAgent"
                  className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div>
                <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">Department</label>
                <select
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                >
                  <option value="Operations">Operations</option>
                  <option value="Finance & Billing">Finance & Billing</option>
                  <option value="Customer Support">Customer Support</option>
                  <option value="Security & Compliance">Security & Compliance</option>
                  <option value="Engineering">Engineering</option>
                </select>
              </div>

              <div>
                <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">Agent Purpose & Scope</label>
                <textarea
                  required
                  rows={3}
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="Automated customer refund processing up to ₹5,000 limit."
                  className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">Autonomy Level</label>
                  <select
                    value={autonomyLevel}
                    onChange={(e) => setAutonomyLevel(e.target.value)}
                    className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                  >
                    <option value="LOW">LOW (Human Approval Required)</option>
                    <option value="MEDIUM">MEDIUM (Threshold Governed)</option>
                    <option value="HIGH">HIGH (Autonomous Standard)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">Daily Budget (₹)</label>
                  <input
                    type="number"
                    required
                    value={dailyBudget}
                    onChange={(e) => setDailyBudget(Number(e.target.value))}
                    className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#E8E8E4]">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[13px] font-bold text-[#666666] hover:bg-[#F0F0EE]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold transition-colors disabled:opacity-50"
                >
                  {submitting ? "Registering..." : "Issue Passport & Register"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
