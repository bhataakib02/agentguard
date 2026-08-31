"use client";

import React, { useEffect, useState } from "react";
import StatusBadge from "@/components/ui/StatusBadge";
import { Radio, Activity, RefreshCw } from "lucide-react";

export default function ActivityFeedPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  useEffect(() => {
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket("ws://localhost:8000/ws");

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.type !== "PONG") {
            setEvents((prev) => [parsed, ...prev.slice(0, 49)]);
          }
        } catch (err) {}
      };

      ws.onclose = () => {
        setWsConnected(false);
      };
    } catch (e) {
      setWsConnected(false);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-5">
        <div>
          <h1 className="text-[24px] font-bold text-[#1F1F1F]">Live Activity Stream</h1>
          <p className="text-[13px] text-[#666666]">
            Real-time WebSocket Broadcast of Agent Runtime Events & Governance Decisions
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] text-[12px] font-bold">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              wsConnected ? "bg-[#2E9D50] animate-pulse" : "bg-[#E53935]"
            }`}
          />
          <span>{wsConnected ? "WebSocket Connected" : "WebSocket Disconnected"}</span>
        </div>
      </div>

      {events.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Radio className="w-12 h-12 text-[#666666] mx-auto animate-pulse opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Awaiting Live WebSocket Broadcast Events</h3>
          <p className="text-[12px] text-[#666666] max-w-md mx-auto">
            The WebSocket listener is active. Perform actions across the AgentGuard platform or run the Action Evaluator on the Dashboard to stream real-time events.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] divide-y divide-[#E8E8E4] shadow-sm">
          {events.map((ev, idx) => (
            <div key={idx} className="p-4 flex items-center justify-between hover:bg-[#FCFCFA] transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[#EAF7EE] flex items-center justify-center text-[#2E9D50]">
                  <Activity className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-bold text-[#1F1F1F]">{ev.type || "EVENT"}</span>
                    {ev.agent_code && <span className="text-[11px] font-bold text-[#8064C8]">{ev.agent_code}</span>}
                  </div>
                  <p className="text-[12px] text-[#666666]">{ev.explanation || ev.action || ev.name || JSON.stringify(ev)}</p>
                </div>
              </div>
              <div className="text-right space-y-1">
                {ev.decision && <StatusBadge status={ev.decision} />}
                <span className="text-[10px] text-[#666666] block">
                  {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "Just now"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
