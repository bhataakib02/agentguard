import React from "react";
import Image from "next/image";
import { Lock, Activity, Bot, Shield } from "lucide-react";

export default function SecurityIllustration() {
  return (
    <div className="w-full h-full flex flex-col justify-center items-center p-6 space-y-8 select-none">
      {/* 3D Shield & Fixed Orbit Outer Container */}
      <div className="relative w-64 h-64 sm:w-72 sm:h-72 flex items-center justify-center">
        {/* 1. Fixed Circular Orbit (Completely Static - Does NOT rotate) */}
        <div className="absolute inset-0 rounded-full border-2 border-dashed border-[#2E9D50]/40 shadow-inner pointer-events-none" />

        {/* 2. Central 3D Clockwise Rotating Shield Container */}
        <div className="absolute w-44 h-44 sm:w-48 sm:h-48 rounded-full bg-[#EAF7EE] flex items-center justify-center border border-[#2E9D50]/30 shadow-inner p-6 overflow-hidden [perspective:1000px]">
          {/* Subtle Metallic/Glass Glare Highlight */}
          <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent pointer-events-none animate-metallic-glare z-10" />

          {/* 3D Central AgentGuard Shield (Rotates Clockwise on Y-axis) */}
          <div className="relative w-28 h-28 sm:w-32 sm:h-32 animate-rotate-3d-shield flex items-center justify-center [transform-style:preserve-3d]">
            {/* Front 3D Shield Face */}
            <div className="absolute inset-0 flex items-center justify-center [transform:translateZ(8px)]">
              <Image
                src="/logo.png"
                alt="AgentGuard 3D Shield Logo"
                width={120}
                height={120}
                className="object-contain filter drop-shadow-[0_8px_16px_rgba(46,157,80,0.35)]"
                priority
              />
            </div>

            {/* Realistic 3D Thickness Extrusion Layers */}
            <div className="absolute inset-0 flex items-center justify-center [transform:translateZ(4px)] opacity-85 pointer-events-none">
              <Image src="/logo.png" alt="" width={120} height={120} className="object-contain filter brightness-90 contrast-125" />
            </div>
            <div className="absolute inset-0 flex items-center justify-center [transform:translateZ(0px)] opacity-65 pointer-events-none">
              <Image src="/logo.png" alt="" width={120} height={120} className="object-contain filter brightness-75 blur-[0.5px]" />
            </div>
            <div className="absolute inset-0 flex items-center justify-center [transform:translateZ(-4px)] opacity-85 pointer-events-none">
              <Image src="/logo.png" alt="" width={120} height={120} className="object-contain filter brightness-90 contrast-125" />
            </div>

            {/* Back 3D Shield Face (Visible when rotated 180deg) */}
            <div className="absolute inset-0 flex items-center justify-center [transform:rotateY(180deg)_translateZ(8px)]">
              <Image
                src="/logo.png"
                alt="AgentGuard 3D Shield Logo Back"
                width={120}
                height={120}
                className="object-contain filter drop-shadow-[0_8px_16px_rgba(46,157,80,0.35)]"
                priority
              />
            </div>
          </div>
        </div>

        {/* 3. Four Surrounding Fixed Icon Badges at Cardinal Positions (Completely Static) */}
        {/* Top: Fixed Robot Icon */}
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 p-3 bg-white border border-[#E8E8E4] rounded-full shadow-md text-[#8064C8] hover:scale-105 transition-transform z-20">
          <Bot className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>

        {/* Right: Fixed Shield/Check Icon */}
        <div className="absolute top-1/2 -right-3 -translate-y-1/2 p-3 bg-white border border-[#E8E8E4] rounded-full shadow-md text-[#2E9D50] hover:scale-105 transition-transform z-20">
          <Shield className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>

        {/* Bottom: Fixed Lock Icon */}
        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 p-3 bg-white border border-[#E8E8E4] rounded-full shadow-md text-[#2878D4] hover:scale-105 transition-transform z-20">
          <Lock className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>

        {/* Left: Fixed Heartbeat/Activity Icon */}
        <div className="absolute top-1/2 -left-3 -translate-y-1/2 p-3 bg-white border border-[#E8E8E4] rounded-full shadow-md text-[#F59A23] hover:scale-105 transition-transform z-20">
          <Activity className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>
      </div>

      {/* Static AgentGuard Text Branding Below Logo */}
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
