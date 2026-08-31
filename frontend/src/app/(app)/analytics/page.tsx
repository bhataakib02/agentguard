"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import KpiCard from "@/components/ui/KpiCard";
import { Activity, Bot, Shield, UserCheck } from "lucide-react";

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadOverview() {
      try {
        const data = await fetchApi("/analytics/overview").catch(() => null);
        setOverview(data || {});
      } catch (err) {
        console.error("Analytics fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadOverview();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Analytics & Intelligence</h1>
        <p className="text-[13px] text-[#666666]">
          Platform Governance Analytics & Aggregate Operational Metrics
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <KpiCard
          label="TOTAL REGISTERED AGENTS"
          value={overview?.total_agents ?? 0}
          icon={Bot}
        />
        <KpiCard
          label="DECISIONS EVALUATED"
          value={overview?.total_decisions ?? 0}
          icon={Shield}
        />
        <KpiCard
          label="PENDING APPROVALS"
          value={overview?.pending_approvals ?? 0}
          icon={UserCheck}
        />
        <KpiCard
          label="AVG PLATFORM RISK SCORE"
          value={`${overview?.avg_risk_score ?? 0} / 100`}
          icon={Activity}
        />
      </div>
    </div>
  );
}
