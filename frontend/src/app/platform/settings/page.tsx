"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Settings,
  Shield,
  Lock,
  Bell,
  FileSearch,
  CheckCircle,
  RefreshCw,
  Save,
  Clock,
  Sliders,
  Globe
} from "lucide-react";

export default function PlatformSettingsPage() {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"general" | "security" | "governance" | "notifications" | "audit">("general");
  const [savedMsg, setSavedMsg] = useState("");

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/platform/settings");
      setSettings(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedMsg("Platform configuration updated successfully!");
    setTimeout(() => setSavedMsg(""), 3000);
  };

  return (
    <div className="space-y-6 text-[#E1E7F0]">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1E2638] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold text-white tracking-tight">Platform Settings</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
              GLOBAL CONFIGURATION
            </span>
          </div>
          <p className="text-[12px] text-[#94A3B8] mt-0.5">
            Super Admin global platform configuration, security controls, governance defaults, and audit retention.
          </p>
        </div>

        <button
          onClick={() => loadSettings()}
          className="px-3.5 py-1.5 bg-[#161C2A] border border-[#232F48] rounded-[8px] text-[#94A3B8] hover:text-white flex items-center gap-2 text-[12px] font-bold self-start sm:self-auto transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#2E9D50]" : ""}`} />
          <span>Reload</span>
        </button>
      </div>

      {/* Toast Notification */}
      {savedMsg && (
        <div className="p-3.5 rounded-[10px] bg-[#173B25] border border-[#2E9D50]/50 text-[#2E9D50] text-[13px] font-bold flex items-center gap-2 shadow-sm">
          <CheckCircle className="w-4 h-4" />
          <span>{savedMsg}</span>
        </div>
      )}

      {/* SETTINGS NAVIGATION TABS */}
      <div className="flex items-center gap-2 border-b border-[#1E2638] pb-1 overflow-x-auto text-[13px] font-bold">
        {[
          { id: "general", label: "General", icon: Globe },
          { id: "security", label: "Security", icon: Lock },
          { id: "governance", label: "Governance", icon: Shield },
          { id: "notifications", label: "Notifications", icon: Bell },
          { id: "audit", label: "Audit & Compliance", icon: FileSearch }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-[8px] transition-colors shrink-0 ${
                isActive
                  ? "bg-[#173B25] text-white border border-[#2E9D50]/50"
                  : "text-[#94A3B8] hover:bg-[#161C2A] hover:text-white"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-[#2E9D50]" : "text-[#64748B]"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT PANELS */}
      <form onSubmit={handleSave} className="bg-[#121722] border border-[#1E2638] rounded-[12px] p-6 space-y-6 shadow-sm">
        {activeTab === "general" && (
          <div className="space-y-4 max-w-2xl text-[13px]">
            <h3 className="font-bold text-white text-[16px] border-b border-[#1E2638] pb-2">General Platform Information</h3>
            
            <div>
              <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Platform Name</label>
              <input
                type="text"
                defaultValue={settings?.general?.platform_name || "AGENTGUARD Platform Control Center"}
                className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Platform Description</label>
              <textarea
                rows={2}
                defaultValue={settings?.general?.platform_description || "Enterprise AI Agent Security, Governance & Multi-Tenant Control Plane"}
                className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Platform Timezone</label>
              <select className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]">
                <option>UTC (Coordinated Universal Time)</option>
                <option>Asia/Kolkata (IST +5:30)</option>
                <option>America/New_York (EST -5:00)</option>
              </select>
            </div>
          </div>
        )}

        {activeTab === "security" && (
          <div className="space-y-4 max-w-2xl text-[13px]">
            <h3 className="font-bold text-white text-[16px] border-b border-[#1E2638] pb-2">Security & Session Configuration</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Session Token TTL (Minutes)</label>
                <input
                  type="number"
                  defaultValue={settings?.security?.session_ttl_minutes || 480}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Idle Timeout (Minutes)</label>
                <input
                  type="number"
                  defaultValue={settings?.security?.idle_timeout_minutes || 60}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Security Enforcement Mode</label>
              <select className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]">
                <option value="STRICT">STRICT (Automatic Block & Quarantine)</option>
                <option value="AUDIT">AUDIT ONLY (Log & Alert)</option>
              </select>
            </div>

            <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between">
              <div>
                <span className="font-bold text-white block">Require Multi-Factor Authentication (MFA) for Super Admin</span>
                <span className="text-[11px] text-[#64748B]">Enforce TOTP hardware/app token for Super Admin login</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] border border-[#2E9D50]/40 font-mono">
                ENABLED
              </span>
            </div>
          </div>
        )}

        {activeTab === "governance" && (
          <div className="space-y-4 max-w-2xl text-[13px]">
            <h3 className="font-bold text-white text-[16px] border-b border-[#1E2638] pb-2">Default Governance Behaviors</h3>
            
            <div>
              <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Default Fallback Action</label>
              <select className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]">
                <option value="REVIEW">REVIEW (Escalate to Human Manager)</option>
                <option value="REFUSE">REFUSE (Block Action Immediately)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">High Risk Threshold (0-100)</label>
                <input
                  type="number"
                  defaultValue={settings?.governance?.global_risk_threshold_high || 75}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Critical Risk Threshold (0-100)</label>
                <input
                  type="number"
                  defaultValue={settings?.governance?.global_risk_threshold_critical || 90}
                  className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]"
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === "notifications" && (
          <div className="space-y-4 max-w-2xl text-[13px]">
            <h3 className="font-bold text-white text-[16px] border-b border-[#1E2638] pb-2">Platform Notifications & Alerts</h3>
            
            <div className="space-y-3">
              <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">Email Alerts</span>
                  <span className="text-[11px] text-[#64748B]">Send critical security alerts to thefreelancer2076@gmail.com</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] font-mono">ACTIVE</span>
              </div>

              <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">Webhook Alert Integration</span>
                  <span className="text-[11px] text-[#64748B]">Broadcast critical security incidents to external Webhooks</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] font-mono">ACTIVE</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === "audit" && (
          <div className="space-y-4 max-w-2xl text-[13px]">
            <h3 className="font-bold text-white text-[16px] border-b border-[#1E2638] pb-2">Audit Retention & Compliance</h3>
            
            <div>
              <label className="block text-[11px] font-bold text-[#94A3B8] uppercase font-mono mb-1">Audit Log Retention Period</label>
              <select className="w-full bg-[#161C2A] border border-[#232F48] rounded-[8px] px-3 py-2 text-white outline-none focus:border-[#2E9D50]">
                <option value="365">365 Days (1 Year Standard)</option>
                <option value="90">90 Days</option>
                <option value="2555">2555 Days (7 Years Enterprise)</option>
              </select>
            </div>

            <div className="p-3 bg-[#161C2A] rounded-[8px] border border-[#232F48] flex items-center justify-between">
              <div>
                <span className="font-bold text-white block">Immutable Provenance Chain</span>
                <span className="text-[11px] text-[#64748B]">Cryptographically hash & link every AI agent decision record</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#173B25] text-[#2E9D50] font-mono">ENFORCED</span>
            </div>
          </div>
        )}

        <div className="pt-4 border-t border-[#1E2638] flex justify-end">
          <button
            type="submit"
            className="px-5 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] font-bold text-[13px] transition-colors flex items-center gap-2 shadow-sm"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </form>
    </div>
  );
}
