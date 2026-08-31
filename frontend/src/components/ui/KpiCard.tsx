import React from "react";
import { LucideIcon } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  subtext?: string;
  iconBgColor?: string;
  iconColor?: string;
}

export default function KpiCard({
  label,
  value,
  icon: Icon,
  subtext,
  iconBgColor = "#EAF7EE",
  iconColor = "#2E9D50",
}: KpiCardProps) {
  return (
    <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-4 space-y-2 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold text-[#666666] uppercase">{label}</span>
        {Icon && (
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ backgroundColor: iconBgColor, color: iconColor }}
          >
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <p className="text-[28px] font-bold text-[#1F1F1F] leading-none">{value}</p>
      {subtext && <span className="text-[11px] font-bold text-[#2E9D50]">{subtext}</span>}
    </div>
  );
}
