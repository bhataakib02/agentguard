import React from "react";
import Image from "next/image";
import SecurityIllustration from "@/components/ui/SecurityIllustration";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#FCFCFA] flex flex-col items-center justify-center p-4 sm:p-6 md:p-8 font-sans">
      {/* Mobile Branding Header (Shown only on mobile < md) */}
      <div className="md:hidden flex flex-col items-center justify-center text-center mb-4 sm:mb-6 pt-2 select-none">
        <div className="relative w-16 h-16 sm:w-20 sm:h-20 mb-2 flex items-center justify-center">
          <Image
            src="/logo.png"
            alt="AgentGuard Logo"
            width={80}
            height={80}
            className="object-contain filter drop-shadow-[0_4px_12px_rgba(46,157,80,0.25)]"
            priority
          />
        </div>
        <h1 className="text-[20px] sm:text-[22px] font-bold text-[#1F1F1F] tracking-tight">
          AGENTGUARD
        </h1>
        <p className="text-[11px] sm:text-[12px] font-bold text-[#2E9D50] uppercase tracking-wide">
          Runtime Control Plane
        </p>
      </div>

      {/* Auth Container Card */}
      <div className="w-full max-w-[440px] md:max-w-[1000px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] shadow-lg grid grid-cols-1 md:grid-cols-2 overflow-hidden">
        {/* Left Side Illustration */}
        <div className="bg-[#FCFCFA] border-r border-[#E8E8E4] hidden md:block">
          <SecurityIllustration />
        </div>

        {/* Right Side Form Content */}
        <div className="p-5 sm:p-8 md:p-10 flex flex-col justify-center">{children}</div>
      </div>
    </div>
  );
}

