"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Bell } from "lucide-react";

export default function NotificationsPage() {
  const [notifs, setNotifs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadNotifs() {
      try {
        const data = await fetchApi("/notifications").catch(() => []);
        setNotifs(data || []);
      } catch (err) {
        console.error("Notifications fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadNotifs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Notifications & Alerts</h1>
        <p className="text-[13px] text-[#666666]">
          Real-Time Governance Alerts & Incident Notifications
        </p>
      </div>

      {notifs.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Bell className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Zero Notifications</h3>
          <p className="text-[12px] text-[#666666]">
            No notification records exist in the database.
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] divide-y divide-[#E8E8E4] shadow-sm">
          {notifs.map((n) => (
            <div key={n.id} className="p-4 flex items-center justify-between hover:bg-[#FCFCFA] transition-colors">
              <div>
                <h3 className="text-[14px] font-bold text-[#1F1F1F]">{n.title}</h3>
                <p className="text-[12px] text-[#666666]">{n.message}</p>
              </div>
              <StatusBadge status={n.severity} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
