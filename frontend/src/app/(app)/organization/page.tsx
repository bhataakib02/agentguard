"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  Building,
  Users,
  Bot,
  Shield,
  CreditCard,
  CheckCircle,
  AlertTriangle,
  Save,
  Palette,
  Image as ImageIcon,
  Trash2,
  RefreshCw
} from "lucide-react";

export default function OrganizationPage() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [brandingSaving, setBrandingSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [brandingMsg, setBrandingMsg] = useState<string | null>(null);

  const [editName, setEditName] = useState("");
  const [editDomain, setEditDomain] = useState("");

  const [editDisplayName, setEditDisplayName] = useState("");
  const [editLogoUrl, setEditLogoUrl] = useState("");

  useEffect(() => {
    async function loadOrgData() {
      setLoading(true);
      try {
        const [dashRes, setRes] = await Promise.all([
          fetchApi("/organization/dashboard").catch(() => null),
          fetchApi("/organization/settings").catch(() => null),
        ]);

        if (dashRes) setDashboard(dashRes);
        if (setRes) {
          setSettings(setRes);
          setEditName(setRes.name || "");
          setEditDomain(setRes.domain || "");
          setEditDisplayName(setRes.display_name || setRes.name || "");
          setEditLogoUrl(setRes.logo_url || "");
        }
      } catch (err) {
        console.error("Failed to load organization data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadOrgData();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);

    try {
      await fetchApi("/organization/settings", {
        method: "PATCH",
        body: JSON.stringify({
          name: editName,
          domain: editDomain,
        }),
      });
      setSaveMsg("Organization workspace settings saved successfully!");
      setDashboard((prev: any) => ({ ...prev, org_name: editName, domain: editDomain }));
    } catch (err: any) {
      setSaveMsg(err.message || "Failed to update organization settings");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(null), 4000);
    }
  };

  const handleSaveBranding = async (e: React.FormEvent) => {
    e.preventDefault();
    setBrandingSaving(true);
    setBrandingMsg(null);

    try {
      const res = await fetchApi("/organization/branding", {
        method: "PATCH",
        body: JSON.stringify({
          name: editName,
          display_name: editDisplayName,
          logo_url: editLogoUrl || null,
        }),
      });
      setBrandingMsg("Organization custom branding updated successfully!");
      setDashboard((prev: any) => ({
        ...prev,
        org_name: res.name,
        display_name: res.display_name,
        logo_url: res.logo_url,
        initials: res.initials,
      }));
    } catch (err: any) {
      setBrandingMsg(err.message || "Failed to update organization branding");
    } finally {
      setBrandingSaving(false);
      setTimeout(() => setBrandingMsg(null), 4000);
    }
  };

  const handleRemoveLogo = async () => {
    setBrandingSaving(true);
    setBrandingMsg(null);

    try {
      const res = await fetchApi("/organization/branding/logo", {
        method: "DELETE",
      });
      setEditLogoUrl("");
      setBrandingMsg("Custom logo removed. Reset to clean organization initials badge.");
      setDashboard((prev: any) => ({
        ...prev,
        logo_url: null,
        initials: res.initials,
      }));
    } catch (err: any) {
      setBrandingMsg(err.message || "Failed to remove custom logo");
    } finally {
      setBrandingSaving(false);
      setTimeout(() => setBrandingMsg(null), 4000);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-[#666666] font-bold animate-pulse">
        Loading organization workspace data & metered license stats...
      </div>
    );
  }

  const metrics = dashboard?.metrics || {
    users: { current: 1, max: 10 },
    ai_agents: { current: 0, max: 5 },
    api_requests: { current: 0, max: 100000, percentage: 0 },
    security_alerts: 0,
    pending_approvals: 0,
  };

  const currentLogo = dashboard?.logo_url || editLogoUrl;
  const currentInitials = dashboard?.initials || editName.substring(0, 2).toUpperCase() || "AG";

  return (
    <div className="space-y-8">
      {/* Header Banner with Dual Logo Branding */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          {currentLogo ? (
            <img
              src={currentLogo}
              alt="Organization Custom Logo"
              className="w-16 h-16 rounded-[14px] object-cover border-2 border-[#8064C8] shadow-md shrink-0"
            />
          ) : (
            <div className="w-16 h-16 rounded-[14px] bg-[#8064C8] text-white flex items-center justify-center text-[22px] font-bold shadow-md shrink-0 border-2 border-[#8064C8]">
              {currentInitials}
            </div>
          )}

          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-[24px] font-bold text-[#1F1F1F]">
                {dashboard?.display_name || dashboard?.org_name || "Enterprise Workspace"}
              </h1>
              <span className="text-[11px] font-bold px-3 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded-full uppercase">
                {dashboard?.status || "ACTIVE"}
              </span>
            </div>
            <p className="text-[13px] text-[#666666] font-mono">
              Tenant ID: {dashboard?.org_id ? String(dashboard.org_id) : "org_id"} • Domain: {dashboard?.domain || "not set"}
            </p>
            <div className="flex items-center gap-3 text-[12px] font-bold pt-0.5">
              <span className="text-[#8064C8] bg-[#F1EDFA] px-2.5 py-0.5 rounded border border-[#8064C8]/20">
                Plan: {dashboard?.plan_id || "STARTER"}
              </span>
              <span className="text-[#2E9D50]">Tenant Boundary Isolated</span>
            </div>
          </div>
        </div>

        <div className="text-right space-y-1 border-l pl-6 border-[#E8E8E4] hidden md:block">
          <span className="text-[11px] text-[#666666] font-bold uppercase block">Platform Identity</span>
          <span className="text-[15px] font-bold text-[#1F1F1F] block">AGENTGUARD SaaS Engine</span>
          <span className="text-[11px] text-[#237A3C] font-bold block">Zero-Trust Isolation</span>
        </div>
      </div>

      {/* Metered License Usage Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* User Quota Card */}
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase">Tenant User License</span>
            <Users className="w-5 h-5 text-[#8064C8]" />
          </div>
          <div>
            <div className="flex items-baseline justify-between">
              <span className="text-[24px] font-bold text-[#1F1F1F]">{metrics.users.current}</span>
              <span className="text-[12px] text-[#666666] font-bold">Max: {metrics.users.max} users</span>
            </div>
            <div className="w-full h-2 bg-[#F0F0ED] rounded-full overflow-hidden mt-2">
              <div
                className="h-full bg-[#8064C8] rounded-full transition-all"
                style={{ width: `${Math.min((metrics.users.current / metrics.users.max) * 100, 100)}%` }}
              />
            </div>
          </div>
          <span className="text-[11px] text-[#666666] block">SUPER_ADMIN excluded from quota</span>
        </div>

        {/* AI Agents Meter */}
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase">AI Agents Capacity</span>
            <Bot className="w-5 h-5 text-[#2E9D50]" />
          </div>
          <div>
            <div className="flex items-baseline justify-between">
              <span className="text-[24px] font-bold text-[#1F1F1F]">{metrics.ai_agents.current}</span>
              <span className="text-[12px] text-[#666666] font-bold">Max: {metrics.ai_agents.max} agents</span>
            </div>
            <div className="w-full h-2 bg-[#F0F0ED] rounded-full overflow-hidden mt-2">
              <div
                className="h-full bg-[#2E9D50] rounded-full transition-all"
                style={{ width: `${Math.min((metrics.ai_agents.current / metrics.ai_agents.max) * 100, 100)}%` }}
              />
            </div>
          </div>
          <span className="text-[11px] text-[#237A3C] font-bold block">Autonomous Agent Guard</span>
        </div>

        {/* Security & Governance Meter */}
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#666666] uppercase">Security & Governance</span>
            <Shield className="w-5 h-5 text-[#E53935]" />
          </div>
          <div className="space-y-1 pt-1">
            <div className="flex items-center justify-between text-[13px]">
              <span className="text-[#666666]">Pending Approvals:</span>
              <span className="font-bold text-[#1F1F1F]">{metrics.pending_approvals}</span>
            </div>
            <div className="flex items-center justify-between text-[13px]">
              <span className="text-[#666666]">Security Alerts:</span>
              <span className="font-bold text-[#E53935]">{metrics.security_alerts}</span>
            </div>
          </div>
          <span className="text-[11px] text-[#237A3C] font-bold block pt-1">Zero-Trust Isolation Active</span>
        </div>
      </div>

      {/* Organization Branding & Custom Identity Form */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-2 border-b border-[#E8E8E4] pb-3">
          <Palette className="w-5 h-5 text-[#8064C8]" />
          <h2 className="text-[18px] font-bold text-[#1F1F1F]">Organization Custom Branding</h2>
        </div>

        {brandingMsg && (
          <div className="p-3 rounded-[8px] bg-[#EAF7EE] border border-[#2E9D50]/30 text-[#237A3C] text-[13px] font-bold">
            {brandingMsg}
          </div>
        )}

        <form onSubmit={handleSaveBranding} className="space-y-5 text-[13px]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Organization Official Name</label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#8064C8]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Organization Display Name / Abbreviation</label>
                <input
                  type="text"
                  placeholder="ACME"
                  value={editDisplayName}
                  onChange={(e) => setEditDisplayName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#8064C8]"
                />
                <span className="text-[11px] text-[#666666] block mt-1">Used in sidebar top bar & navigation tabs</span>
              </div>

              <div>
                <label className="block font-bold text-[#1F1F1F] mb-1">Organization Custom Logo URL</label>
                <input
                  type="text"
                  placeholder="https://acme.com/assets/logo.png"
                  value={editLogoUrl}
                  onChange={(e) => setEditLogoUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#8064C8] font-mono text-[12px]"
                />
                <span className="text-[11px] text-[#666666] block mt-1">Supports PNG, JPG, WEBP, SVG transparent backgrounds</span>
              </div>
            </div>

            {/* Logo Preview Card */}
            <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] p-5 space-y-3 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-bold text-[#666666] uppercase block mb-3">Live Logo Preview</span>
                <div className="flex items-center gap-4">
                  {editLogoUrl ? (
                    <img
                      src={editLogoUrl}
                      alt="Custom Logo Preview"
                      className="w-20 h-20 rounded-[12px] object-cover border-2 border-[#8064C8] shadow"
                      onError={() => {}}
                    />
                  ) : (
                    <div className="w-20 h-20 rounded-[12px] bg-[#8064C8] text-white flex items-center justify-center text-[28px] font-bold shadow border-2 border-[#8064C8]">
                      {currentInitials}
                    </div>
                  )}
                  <div>
                    <span className="font-bold text-[#1F1F1F] text-[16px] block">
                      {editDisplayName || editName || "Acme Technologies"}
                    </span>
                    <span className="text-[11px] text-[#2E9D50] font-bold block mt-0.5">
                      {editLogoUrl ? "Custom Logo Active" : "Clean Fallback Initials Badge Active"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={brandingSaving}
                  className="flex items-center gap-2 px-4 py-2 bg-[#8064C8] hover:bg-[#6C52B0] text-white font-bold rounded-[8px] transition-colors"
                >
                  <Save className="w-4 h-4" />
                  <span>{brandingSaving ? "Saving..." : "Save Branding"}</span>
                </button>

                {editLogoUrl && (
                  <button
                    type="button"
                    onClick={handleRemoveLogo}
                    disabled={brandingSaving}
                    className="flex items-center gap-1.5 px-3 py-2 bg-[#FFFFFF] border border-[#E8E8E4] text-[#E53935] hover:bg-[#FDECEC] font-bold rounded-[8px] transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span>Reset to Initials</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </form>
      </div>

      {/* Subscription & License Detail Card */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-[#8064C8]" />
            <h2 className="text-[18px] font-bold text-[#1F1F1F]">Subscription License Status</h2>
          </div>
          <span className="text-[12px] font-bold px-3 py-1 bg-[#EAF7EE] text-[#237A3C] rounded-full border border-[#2E9D50]/30 uppercase flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5" />
            {dashboard?.license_status || "ACTIVE"}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[13px]">
          <div className="space-y-1">
            <span className="text-[#666666] font-bold block text-[11px] uppercase">Current Plan</span>
            <span className="text-[16px] font-bold text-[#8064C8] block">{dashboard?.plan_id || "STARTER"}</span>
            <span className="text-[11px] text-[#666666]">Managed by Platform Super Admin</span>
          </div>

          <div className="space-y-1">
            <span className="text-[#666666] font-bold block text-[11px] uppercase">License Expiry</span>
            <span className="text-[14px] font-bold text-[#1F1F1F] block">
              {dashboard?.expiry_date ? new Date(dashboard.expiry_date).toLocaleDateString() : "No Expiry / Annual Renewal"}
            </span>
            <span className="text-[11px] text-[#237A3C] font-bold">Automatic Renewal Active</span>
          </div>

          <div className="space-y-1">
            <span className="text-[#666666] font-bold block text-[11px] uppercase">Billing Model</span>
            <span className="text-[14px] font-bold text-[#1F1F1F] block">Enterprise Subscription</span>
            <span className="text-[11px] text-[#666666]">No payment cards stored locally</span>
          </div>
        </div>
      </div>

      {/* Organization Settings Update Form */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 space-y-4 shadow-sm">
        <h2 className="text-[18px] font-bold text-[#1F1F1F]">Organization Workspace Settings</h2>

        {saveMsg && (
          <div className="p-3 rounded-[8px] bg-[#EAF7EE] border border-[#2E9D50]/30 text-[#237A3C] text-[13px] font-bold">
            {saveMsg}
          </div>
        )}

        <form onSubmit={handleSaveSettings} className="space-y-4 max-w-lg text-[13px]">
          <div>
            <label className="block font-bold text-[#1F1F1F] mb-1">Organization Name</label>
            <input
              type="text"
              required
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
            />
          </div>

          <div>
            <label className="block font-bold text-[#1F1F1F] mb-1">Workspace Domain</label>
            <input
              type="text"
              placeholder="acme.com"
              value={editDomain}
              onChange={(e) => setEditDomain(e.target.value)}
              className="w-full px-3 py-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] outline-none focus:border-[#2E9D50]"
            />
          </div>

          <div>
            <label className="block font-bold text-[#666666] mb-1">Tenant Administrator Email</label>
            <input
              type="text"
              disabled
              value={settings?.admin_email || "admin@agentguard.com"}
              className="w-full px-3 py-2 bg-[#F5F5F0] border border-[#E8E8E4] rounded-[8px] text-[#666666] cursor-not-allowed font-mono text-[12px]"
            />
            <span className="text-[11px] text-[#666666] block mt-1">Designated Organization Admin</span>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[8px] transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? "Saving Changes..." : "Save Workspace Settings"}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
