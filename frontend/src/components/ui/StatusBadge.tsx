import React from "react";

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const s = (status || "").toUpperCase();

  if (["ALLOW", "ACTIVE", "VERIFIED", "NORMAL", "HEALTHY", "CONNECTED", "SUCCESS", "PASSED", "APPROVED"].includes(s)) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30">
        ● {s}
      </span>
    );
  }

  if (["REVIEW", "WARNING", "PENDING", "RESTRICTED", "INVESTIGATING", "MEDIUM"].includes(s)) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FFF4D9] text-[#A56300] border border-[#F59A23]/30">
        ▲ {s}
      </span>
    );
  }

  if (["REFUSE", "BLOCKED", "SUSPENDED", "CIRCUIT_BREAK", "CRITICAL", "HIGH", "FAILED", "REJECTED", "EXPIRED", "REVOKED", "DANGER"].includes(s)) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FDECEC] text-[#C62828] border border-[#E53935]/30">
        ✕ {s}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#F0F0EE] text-[#666666] border border-[#E8E8E4]">
      {s || "UNKNOWN"}
    </span>
  );
}
