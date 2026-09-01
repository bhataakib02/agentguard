"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { Users, Search, RefreshCw, Lock, CheckCircle, Shield } from "lucide-react";

export default function PlatformUsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/users");
      setUsers(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleToggleStatus = async (userId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
    try {
      await fetchApi(`/platform/users/${userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus })
      });
      loadUsers();
    } catch (err: any) {
      alert("Status change failed: " + err.message);
    }
  };

  const filtered = users.filter((u) =>
    u.full_name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.org_name.toLowerCase().includes(search.toLowerCase()) ||
    u.role.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">Global Users Directory</h1>
          <p className="text-[12px] text-[#64748B]">Human user accounts across all customer tenant organizations</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 text-[#64748B] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search users..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[12px] text-white outline-none focus:border-[#2E9D50]"
            />
          </div>

          <button
            onClick={() => loadUsers()}
            className="p-2 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-5 space-y-4 shadow-sm">
        <div className="overflow-x-auto border border-[#1E2638] rounded-[8px]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161C2A] border-b border-[#1E2638] text-[10px] font-bold text-[#64748B] uppercase tracking-wider font-mono">
              <tr>
                <th className="py-3 px-4">User Name</th>
                <th className="py-3 px-4">Email Address</th>
                <th className="py-3 px-4">Tenant Organization</th>
                <th className="py-3 px-4">IAM Role</th>
                <th className="py-3 px-4">Department</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2638]">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-[#64748B]">
                    Loading user accounts from Supabase PostgreSQL...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-[#64748B]">
                    No users found matching search query.
                  </td>
                </tr>
              ) : (
                filtered.map((u) => (
                  <tr key={u.id} className="hover:bg-[#161C2A] transition-colors">
                    <td className="py-3.5 px-4 font-bold text-white">{u.full_name}</td>
                    <td className="py-3.5 px-4 font-mono text-[#94A3B8]">{u.email}</td>
                    <td className="py-3.5 px-4 font-bold text-[#2E9D50]">{u.org_name}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/30 font-mono">
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-[#94A3B8]">{u.department}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50]">
                        {u.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleToggleStatus(u.id, u.status)}
                        className="px-2.5 py-1 bg-[#161C2A] border border-[#232F48] rounded-[6px] text-[11px] font-bold text-[#E53935] hover:bg-[#3B1516]"
                      >
                        {u.status === "ACTIVE" ? "Suspend" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
