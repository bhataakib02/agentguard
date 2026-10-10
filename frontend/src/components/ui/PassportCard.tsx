import React from "react";
import StatusBadge from "./StatusBadge";
import { Bot, ShieldCheck, Lock, CheckCircle2, AlertTriangle } from "lucide-react";

interface PassportCardProps {
  agent: any;
  passportNumber: string;
  digitalSignature: string;
  algorithm?: string;
  keyId?: string;
  verificationStatus?: string;
  onVerify?: () => void;
  verifying?: boolean;
}

export default function PassportCard({
  agent,
  passportNumber,
  digitalSignature,
  algorithm = "Ed25519",
  keyId = "agentguard-root-ed25519-v1",
  verificationStatus = "VERIFIED",
  onVerify,
  verifying = false
}: PassportCardProps) {
  const isVerified = verificationStatus === "VERIFIED";

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
        <div className="flex items-center gap-2">
          {onVerify && (
            <button
              onClick={onVerify}
              disabled={verifying}
              className="px-3 py-1 bg-[#FCFCFA] hover:bg-[#F4F4F0] border border-[#E8E8E4] rounded-[6px] text-[11px] font-bold text-[#1F1F1F] flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-[#2E9D50]" />
              <span>{verifying ? "Verifying..." : "Verify Signature"}</span>
            </button>
          )}
          <StatusBadge status={agent.status} />
        </div>
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
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold text-[#8064C8] uppercase flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            <span>Cryptographic Digital Signature ({algorithm})</span>
          </span>
          <span className="text-[10px] font-mono text-[#666666]">Key: {keyId}</span>
        </div>
        <p className="font-mono text-[11px] text-[#1F1F1F] break-all">{digitalSignature}</p>
      </div>

      <div className="pt-2 border-t border-[#E8E8E4] flex items-center justify-between text-[11px] text-[#666666]">
        <span>Issued by AGENTGUARD Central Identity Registry</span>
        <span className="flex items-center gap-1">
          {isVerified ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-[#2E9D50]" />
              <span className="font-bold text-[#2E9D50]">Ed25519 VERIFIED</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-[#E53935]" />
              <span className="font-bold text-[#E53935]">{verificationStatus}</span>
            </>
          )}
        </span>
      </div>
    </div>
  );
}

