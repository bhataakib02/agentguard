import React from "react";
import Image from "next/image";
import { Lock, Activity, Bot } from "lucide-react";

export default function SecurityIllustration() {
  return (
    <div className="w-full h-full flex flex-col justify-center items-center p-6 space-y-6">
      <div className="relative w-64 h-64 flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border-2 border-dashed border-[#2E9D50]/40 animate-spin" style={{ animationDuration: '30s' }}></div>
        <div className="absolute w-48 h-48 rounded-full bg-[#EAF7EE] flex items-center justify-center border border-[#2E9D50]/30 shadow-inner p-8">
          <Image
            src="/logo.png"
            alt="AgentGuard Logo"
            width={120}
            height={120}
            className="object-contain drop-shadow-md"
          />
        </div>
        <div className="absolute top-2 right-4 p-3 bg-white border border-[#E8E8E4] rounded-full shadow-sm text-[#8064C8]">
          <Bot className="w-6 h-6" />
        </div>
        <div className="absolute bottom-4 left-2 p-3 bg-white border border-[#E8E8E4] rounded-full shadow-sm text-[#2878D4]">
          <Lock className="w-6 h-6" />
        </div>
        <div className="absolute top-1/2 -left-4 p-3 bg-white border border-[#E8E8E4] rounded-full shadow-sm text-[#F59A23]">
          <Activity className="w-6 h-6" />
        </div>
      </div>

      <div className="text-center space-y-2 max-w-sm">
        <h2 className="text-[26px] font-bold text-[#1F1F1F] tracking-tight">AGENTGUARD</h2>
        <p className="text-[13px] font-bold text-[#2E9D50] uppercase tracking-wide">
          Runtime Control Plane for Autonomous AI
        </p>
        <p className="text-[12px] text-[#666666] leading-relaxed">
          Zero-Trust Governance Pipeline • Right-to-Refuse Engine • Causal Provenance Black Box
        </p>
      </div>
    </div>
  );
}
