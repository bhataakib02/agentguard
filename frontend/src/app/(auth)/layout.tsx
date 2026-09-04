import React from "react";
import SecurityIllustration from "@/components/ui/SecurityIllustration";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#FCFCFA] flex items-center justify-center p-3 sm:p-6 md:p-8 font-sans">
      <div className="w-full max-w-[1000px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] shadow-lg grid grid-cols-1 md:grid-cols-2 overflow-hidden">
        {/* Left Side Illustration */}
        <div className="bg-[#FCFCFA] border-r border-[#E8E8E4] hidden md:block">
          <SecurityIllustration />
        </div>

        {/* Right Side Form Content */}
        <div className="p-4 sm:p-8 md:p-10 flex flex-col justify-center">{children}</div>
      </div>
    </div>
  );
}
