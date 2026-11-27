"use client";

import React, { useEffect, useState, useCallback } from "react";
import { fetchApi } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { Bell, Check, CheckCheck, Trash2, RefreshCw, Filter, AlertTriangle } from "lucide-react";

export default function NotificationsPage() {
  const [notifs, setNotifs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"ALL" | "UNREAD" | "CRITICAL" | "APPROVALS">("ALL");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [unreadTotal, setUnreadTotal] = useState<number | null>(null);
  const pageSize = 20;

  const loadNotifs = useCallback(async (targetPage = page) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(targetPage * pageSize),
      });
      if (filter === "UNREAD") params.set("unread_only", "true");
      const [data, unreadRes] = await Promise.all([
        fetchApi(`/notifications?${params.toString()}`).catch(() => []),
        fetchApi("/notifications/unread-count").catch(() => null),
      ]);
      const items = data || [];
      setNotifs(items);
      setHasMore(items.length === pageSize);
      if (unreadRes && typeof unreadRes.unread_count === "number") {
        setUnreadTotal(unreadRes.unread_count);
      }
    } catch (err) {
      console.error("Notifications fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    loadNotifs(page);
  }, [loadNotifs, page]);

  const handleMarkOneRead = async (id: string) => {
    setActionLoading(id);
    try {
      await fetchApi(`/notifications/${id}/read`, { method: "PATCH" });
      setNotifs((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read: true } : n))
      );
      setUnreadTotal((prev) => (prev !== null ? Math.max(0, prev - 1) : null));
    } catch (err) {
      console.error("Mark read error:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkAllRead = async () => {
    setActionLoading("ALL");
    try {
      await fetchApi("/notifications/read-all", { method: "POST" });
      setNotifs((prev) => prev.map((n) => ({ ...n, is_read: true, read: true })));
      setUnreadTotal(0);
    } catch (err) {
      console.error("Mark all read error:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: string) => {
    setActionLoading(`del-${id}`);
    try {
      const target = notifs.find((n) => n.id === id);
      await fetchApi(`/notifications/${id}`, { method: "DELETE" });
      setNotifs((prev) => prev.filter((n) => n.id !== id));
      if (target && !target.is_read && !target.read) {
        setUnreadTotal((prev) => (prev !== null ? Math.max(0, prev - 1) : null));
      }
    } catch (err) {
      console.error("Delete notification error:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const unreadCount = unreadTotal !== null
    ? unreadTotal
    : notifs.filter((n) => !n.is_read && !n.read).length;

  const filteredNotifs = notifs.filter((n) => {
    if (filter === "UNREAD") return !n.is_read && !n.read;
    if (filter === "CRITICAL") return n.severity === "CRITICAL" || n.severity === "HIGH";
    if (filter === "APPROVALS") return (n.type || "").toUpperCase().includes("APPROVAL");
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E8E8E4] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">Notifications & Alerts</h1>
            {unreadCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/20 font-mono">
                {unreadCount} UNREAD
              </span>
            )}
          </div>
          <p className="text-[13px] text-[#666666] mt-0.5">
            Real-Time Governance Alerts, Security Incidents & Application Events
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              disabled={actionLoading === "ALL"}
              className="px-3.5 py-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] text-[#1F1F1F] hover:bg-[#FCFCFA] flex items-center gap-2 text-[12px] font-bold shadow-sm transition-colors"
            >
              <CheckCheck className="w-4 h-4 text-[#2E9D50]" />
              <span>Mark all as read</span>
            </button>
          )}

          <button
            onClick={() => loadNotifs(page)}
            disabled={loading}
            className="px-3.5 py-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] text-[#666666] hover:text-[#1F1F1F] flex items-center gap-2 text-[12px] font-bold shadow-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-[#E8E8E4] pb-2 text-[12px] font-bold">
        {[
          { id: "ALL", label: `All (${notifs.length})` },
          { id: "UNREAD", label: `Unread (${unreadCount})` },
          { id: "CRITICAL", label: "Critical & High" },
          { id: "APPROVALS", label: "Approvals" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setPage(0);
              setFilter(tab.id as any);
            }}
            className={`px-3 py-1.5 rounded-[6px] transition-colors ${
              filter === tab.id
                ? "bg-[#1F1F1F] text-white"
                : "text-[#666666] hover:bg-[#F0F0ED] hover:text-[#1F1F1F]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Notifications List */}
      {loading ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center text-[#666666] text-[13px]">
          Loading notifications and alerts...
        </div>
      ) : filteredNotifs.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-3">
          <Bell className="w-10 h-10 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">
            {filter === "UNREAD" ? "Zero Unread Notifications" : "Zero Notifications"}
          </h3>
          <p className="text-[12px] text-[#666666]">
            {filter === "UNREAD"
              ? "All notifications have been marked as read."
              : "No notification records match the current filter."}
          </p>
        </div>
      ) : (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] divide-y divide-[#E8E8E4] shadow-sm">
          {filteredNotifs.map((n) => {
            const isUnread = !n.is_read && !n.read;
            return (
              <div
                key={n.id}
                className={`p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors ${
                  isUnread ? "bg-[#F7FBF8] border-l-4 border-l-[#2E9D50]" : "hover:bg-[#FCFCFA]"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className={`text-[14px] ${isUnread ? "font-bold text-[#1F1F1F]" : "font-medium text-[#444444]"}`}>
                      {n.title}
                    </h3>
                    <StatusBadge status={n.severity || "INFO"} />
                    <span className="text-[10px] text-[#666666] uppercase font-mono px-1.5 py-0.5 bg-[#F0F0ED] rounded">
                      {n.type || "ALERT"}
                    </span>
                  </div>
                  <p className="text-[12px] text-[#666666] leading-relaxed max-w-3xl">{n.message}</p>
                  {n.created_at && (
                    <span className="text-[11px] text-[#999999] font-mono block">
                      {new Date(n.created_at).toLocaleString()}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                  {isUnread && (
                    <button
                      onClick={() => handleMarkOneRead(n.id)}
                      disabled={actionLoading === n.id}
                      title="Mark as read"
                      className="px-2.5 py-1.5 bg-[#FFFFFF] border border-[#E8E8E4] hover:border-[#2E9D50] hover:text-[#2E9D50] text-[#666666] rounded-[6px] text-[11px] font-bold flex items-center gap-1 transition-colors shadow-sm"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Mark read</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(n.id)}
                    disabled={actionLoading === `del-${n.id}`}
                    title="Dismiss notification"
                    className="p-1.5 text-[#999999] hover:text-[#E53935] hover:bg-[#FDECEC] rounded-[6px] transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {!loading && (page > 0 || hasMore) && (
        <div className="flex items-center justify-between pt-2 text-[12px]">
          <span className="text-[#666666] font-mono">Page {page + 1}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] font-bold text-[#1F1F1F] disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
              className="px-3 py-1.5 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[6px] font-bold text-[#1F1F1F] disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
