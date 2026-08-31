import React from "react";
import StatusBadge from "./StatusBadge";
import { Bot, ShieldCheck, QrCode, Lock } from "lucide-react";

interface PassportCardProps {
  agent: any;
  passportNumber: string;
  digitalSignature: string;
}

export default function PassportCard({ agent, passportNumber, digitalSignature }: PassportCardProps) {
  return (
    <div className="bg-[#FFFFFF] border-2 border-[#2E9D50] rounded-[16px] p-6 shadow-md max-w-[650px] mx-auto space-y-5">
      <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-[#EAF7EE] flex items-center justify-center text-[#2E9D50] border border-[#2E9D50]/30">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-[22px] font-bold text-[#1F1F1F] leading-tight">{agent.name}</h2>
            <span className="text-[12px] font-bold text-[#2E9D50]">{agent.agent_code} — {agent.department}</span>
          </div>
        </div>
        <StatusBadge status={agent.status} />
      </div>

      <div className="grid grid-cols-2 gap-4 text-[13px]">
        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">PASSPORT NUMBER</span>
          <strong className="font-mono text-[#2878D4] text-[13px]">{passportNumber}</strong>
        </div>
        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">AUTONOMY LEVEL</span>
          <strong className="text-[#1F1F1F]">{agent.autonomy_level}</strong>
        </div>
        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">MODEL ARCHITECTURE</span>
          <strong className="text-[#8064C8]">{agent.model_name} (v{agent.model_version})</strong>
        </div>
        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
          <span className="text-[11px] font-bold text-[#666666] uppercase block">DAILY BUDGET LIMIT</span>
          <strong className="text-[#2E9D50]">₹{agent.daily_budget ? agent.daily_budget.toLocaleString() : "0"}.00</strong>
        </div>
      </div>

      <div className="p-3 bg-[#F1EDFA] border border-[#8064C8]/30 rounded-[10px] space-y-1">
        <span className="text-[11px] font-bold text-[#8064C8] uppercase flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5" />
          <span>Cryptographic Digital Signature</span>
        </span>
        <p className="font-mono text-[11px] text-[#1F1F1F] break-all">{digitalSignature}</p>
      </div>

      <div className="pt-2 border-t border-[#E8E8E4] flex items-center justify-between text-[11px] text-[#666666]">
        <span>Issued by AGENTGUARD Central Identity Registry</span>
        <span>Status: VERIFIED</span>
      </div>
    </div>
  );
}
