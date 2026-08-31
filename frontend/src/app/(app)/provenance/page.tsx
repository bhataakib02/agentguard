"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { GitFork, User, Bot, Wrench, ShieldCheck } from "lucide-react";

function ProvenanceContent() {
  const searchParams = useSearchParams();
  const decisionId = searchParams.get("id") || "";
  const [events, setEvents] = useState<any[]>([]);
  const [selectedTree, setSelectedTree] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProvenance() {
      try {
        setLoading(true);
        const data = await fetchApi("/provenance/events").catch(() => []);
        setEvents(data || []);
        if (data && data.length > 0) {
          const match = decisionId ? data.find((e: any) => e.decision_id === decisionId || e.id === decisionId) : data[0];
          setSelectedTree(match?.causal_chain_json || data[0].causal_chain_json);
        }
      } catch (err) {
        console.error("Provenance fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadProvenance();
  }, [decisionId]);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Causal Provenance Graph</h1>
        <p className="text-[13px] text-[#666666]">
          Root-Cause Lineage Trace: Human Intent → AI Agent → Tool Invocation → Governance Outcome
        </p>
      </div>

      {events.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <GitFork className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Provenance Traces Recorded</h3>
          <p className="text-[12px] text-[#666666]">
            No causal provenance tree entries exist in the database. Execute a decision from the Action Evaluator to generate lineage traces.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Trace Event Selector */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-4 space-y-3 shadow-sm">
            <h2 className="text-[14px] font-bold text-[#1F1F1F] uppercase text-[11px] text-[#666666]">Recorded Provenance Traces</h2>
            <div className="space-y-2">
              {events.map((ev) => (
                <button
                  key={ev.id}
                  onClick={() => setSelectedTree(ev.causal_chain_json)}
                  className={`w-full text-left p-3 rounded-[8px] border text-[12px] transition-colors ${
                    selectedTree?.decision_id === ev.decision_id
                      ? "bg-[#EAF7EE] border-[#2E9D50] text-[#1F1F1F] font-bold"
                      : "bg-[#FCFCFA] border-[#E8E8E4] text-[#666666] hover:border-[#2E9D50]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#8064C8]">{ev.causal_chain_json?.primary_agent?.id || "AG-000"}</span>
                    <StatusBadge status={ev.causal_chain_json?.governance_decision || "ALLOW"} />
                  </div>
                  <span className="text-[11px] block mt-1">{ev.causal_chain_json?.action_executed || "Action"}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Lineage Visualizer */}
          <div className="lg:col-span-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-6 shadow-sm">
            {selectedTree ? (
              <>
                <div className="border-b border-[#E8E8E4] pb-4">
                  <h2 className="text-[18px] font-bold text-[#1F1F1F]">Causal Execution Tree</h2>
                  <p className="text-[12px] text-[#666666]">
                    Decision ID: <span className="font-mono text-[#8064C8]">{selectedTree.decision_id}</span>
                  </p>
                </div>

                <div className="space-y-4 relative before:absolute before:left-6 before:top-4 before:bottom-4 before:w-0.5 before:bg-[#E8E8E4]">
                  {/* Step 1: Human Initiator */}
                  <div className="relative flex items-start gap-4">
                    <div className="w-12 h-12 rounded-full bg-[#EAF7EE] flex items-center justify-center text-[#2E9D50] z-10 border border-[#2E9D50]/30">
                      <User className="w-5 h-5" />
                    </div>
                    <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex-1 space-y-1">
                      <span className="text-[11px] font-bold text-[#2E9D50] uppercase">1. HUMAN INITIATOR</span>
                      <p className="text-[13px] font-bold text-[#1F1F1F]">
                        {selectedTree.root_initiator?.label || "Authenticated Manager"}
                      </p>
                    </div>
                  </div>

                  {/* Step 2: Primary AI Agent */}
                  <div className="relative flex items-start gap-4">
                    <div className="w-12 h-12 rounded-full bg-[#F1EDFA] flex items-center justify-center text-[#8064C8] z-10 border border-[#8064C8]/30">
                      <Bot className="w-5 h-5" />
                    </div>
                    <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex-1 space-y-1">
                      <span className="text-[11px] font-bold text-[#8064C8] uppercase">2. PRIMARY AI AGENT</span>
                      <p className="text-[13px] font-bold text-[#1F1F1F]">
                        {selectedTree.primary_agent?.label || "AI Agent"}
                      </p>
                    </div>
                  </div>

                  {/* Step 3: Tool Invocation */}
                  <div className="relative flex items-start gap-4">
                    <div className="w-12 h-12 rounded-full bg-[#FFF4D9] flex items-center justify-center text-[#F59A23] z-10 border border-[#F59A23]/30">
                      <Wrench className="w-5 h-5" />
                    </div>
                    <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex-1 space-y-1">
                      <span className="text-[11px] font-bold text-[#F59A23] uppercase">3. TOOL & RESOURCE INVOCATION</span>
                      <p className="text-[13px] font-bold text-[#1F1F1F]">
                        {selectedTree.tool_invoked?.label || "Service API"} (Amount: ₹{selectedTree.impact_amount ? selectedTree.impact_amount.toLocaleString() : "0"})
                      </p>
                    </div>
                  </div>

                  {/* Step 4: Governance Outcome */}
                  <div className="relative flex items-start gap-4">
                    <div className="w-12 h-12 rounded-full bg-[#EAF7EE] flex items-center justify-center text-[#2E9D50] z-10 border border-[#2E9D50]/30">
                      <ShieldCheck className="w-5 h-5" />
                    </div>
                    <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#2E9D50] uppercase">4. GOVERNANCE DECISION</span>
                        <StatusBadge status={selectedTree.governance_decision} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Causal Chain Log */}
                {selectedTree.causal_chain && (
                  <div className="p-4 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2">
                    <span className="text-[11px] font-bold text-[#666666] uppercase block">EXPLICIT CAUSAL CHAIN LOG</span>
                    <ul className="space-y-1 text-[12px] text-[#1F1F1F] font-mono">
                      {selectedTree.causal_chain.map((step: string, idx: number) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12 text-[#666666]">Select a trace on the left to inspect causal lineage.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProvenancePage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-[#666666]">Loading Provenance Graph...</div>}>
      <ProvenanceContent />
    </Suspense>
  );
}
