"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { GitFork, Bot } from "lucide-react";

export default function AgentNetworkPage() {
  const [graph, setGraph] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadGraph() {
      try {
        const data = await fetchApi("/agent-network/graph").catch(() => null);
        setGraph(data || { nodes: [], edges: [] });
      } catch (err) {
        console.error("Agent network fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadGraph();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Multi-Agent Network Topology</h1>
        <p className="text-[13px] text-[#666666]">
          Inter-Agent Trust Graph & Delegation Boundaries
        </p>
      </div>

      {!graph || graph.nodes.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <GitFork className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Network Relationships</h3>
          <p className="text-[12px] text-[#666666]">
            No multi-agent network relationships exist in the database.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {graph.nodes.map((n: any) => (
            <div key={n.id} className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-4 flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-[#EAF7EE] flex items-center justify-center text-[#2E9D50]">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-[13px] font-bold text-[#1F1F1F]">{n.label}</h3>
                  <span className="text-[11px] text-[#666666]">Type: {n.type}</span>
                </div>
              </div>
              <StatusBadge status={n.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
