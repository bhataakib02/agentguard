"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import PassportCard from "@/components/ui/PassportCard";
import { ArrowLeft, Bot, RefreshCw, ChevronDown, Key, Copy, Check, Plus, AlertCircle, RotateCcw, Trash2, Terminal } from "lucide-react";

function PassportContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialAgentId = searchParams.get("id") || "";

  const [agents, setAgents] = useState<any[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>(initialAgentId);
  const [passportData, setPassportData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingPassport, setLoadingPassport] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Verification state
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<any>(null);

  // Credentials state
  const [credentials, setCredentials] = useState<any[]>([]);
  const [loadingCreds, setLoadingCreds] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyResult, setNewKeyResult] = useState<any>(null);
  const [creatingKey, setCreatingKey] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  // 1. Fetch available tenant agents
  useEffect(() => {
    async function loadTenantAgents() {
      setLoading(true);
      setErrorMsg(null);
      try {
        const agentList = await fetchApi("/agents").catch(() => []);
        const validAgents = Array.isArray(agentList) ? agentList : [];
        setAgents(validAgents);

        if (initialAgentId) {
          setSelectedAgentId(initialAgentId);
        } else if (validAgents.length > 0) {
          setSelectedAgentId(validAgents[0].id);
        }
      } catch (err: any) {
        console.error("Failed to load tenant agents:", err);
        setErrorMsg(err.message || "Failed to load agent directory.");
      } finally {
        setLoading(false);
      }
    }
    loadTenantAgents();
  }, [initialAgentId]);

  // 2. Fetch specific agent passport and credentials when selectedAgentId changes
  useEffect(() => {
    if (!selectedAgentId) {
      setPassportData(null);
      setCredentials([]);
      return;
    }

    async function loadPassportAndCredentials() {
      setLoadingPassport(true);
      setLoadingCreds(true);
      setErrorMsg(null);
      setVerificationResult(null);

      try {
        const [passRes, credsRes] = await Promise.all([
          fetchApi(`/agents/${selectedAgentId}/passport`),
          fetchApi(`/agents/${selectedAgentId}/credentials`).catch(() => [])
        ]);
        setPassportData(passRes);
        setCredentials(Array.isArray(credsRes) ? credsRes : []);
      } catch (err: any) {
        console.error("Passport fetch error:", err);
        setErrorMsg(err.message || "Unable to retrieve cryptographic passport for this agent.");
        setPassportData(null);
      } finally {
        setLoadingPassport(false);
        setLoadingCreds(false);
      }
    }

    loadPassportAndCredentials();
  }, [selectedAgentId]);

  const handleSelectAgent = (newId: string) => {
    setSelectedAgentId(newId);
    router.replace(`/agents/passport?id=${newId}`);
  };

  const handleVerifySignature = async () => {
    if (!selectedAgentId) return;
    setVerifying(true);
    try {
      const res = await fetchApi(`/agents/${selectedAgentId}/passport/verify`);
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationResult({
        valid: false,
        status: "FAILED",
        reason: err.message || "Cryptographic verification call failed."
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleCreateCredential = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgentId) return;
    setCreatingKey(true);
    try {
      const res = await fetchApi(`/agents/${selectedAgentId}/credentials`, {
        method: "POST",
        body: JSON.stringify({
          name: newKeyName || "Machine Production Key",
          credential_type: "API_KEY"
        })
      });
      setNewKeyResult(res);
      setNewKeyName("");
      // Refresh credentials list
      const updatedCreds = await fetchApi(`/agents/${selectedAgentId}/credentials`).catch(() => []);
      setCredentials(Array.isArray(updatedCreds) ? updatedCreds : []);
    } catch (err: any) {
      alert(`Error generating credential: ${err.message}`);
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRotateCredential = async (credId: string) => {
    if (!selectedAgentId || !confirm("Are you sure you want to rotate this machine credential? The old key will immediately become invalid.")) return;
    try {
      const res = await fetchApi(`/agents/${selectedAgentId}/credentials/${credId}/rotate`, {
        method: "POST",
        body: JSON.stringify({ name: "Rotated Service Key" })
      });
      setNewKeyResult(res);
      setShowKeyModal(true);
      const updatedCreds = await fetchApi(`/agents/${selectedAgentId}/credentials`).catch(() => []);
      setCredentials(Array.isArray(updatedCreds) ? updatedCreds : []);
    } catch (err: any) {
      alert(`Error rotating credential: ${err.message}`);
    }
  };

  const handleRevokeCredential = async (credId: string) => {
    if (!selectedAgentId || !confirm("Are you sure you want to revoke this credential? All automated calls using it will fail.")) return;
    try {
      await fetchApi(`/agents/${selectedAgentId}/credentials/${credId}`, {
        method: "DELETE"
      });
      const updatedCreds = await fetchApi(`/agents/${selectedAgentId}/credentials`).catch(() => []);
      setCredentials(Array.isArray(updatedCreds) ? updatedCreds : []);
    } catch (err: any) {
      alert(`Error revoking credential: ${err.message}`);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E8E8E4] pb-5">
        <div className="flex items-center gap-3">
          <Link href="/agents" className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] hover:bg-[#FCFCFA]">
            <ArrowLeft className="w-4 h-4 text-[#666666]" />
          </Link>
          <div>
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">Cryptographic Agent Passport & Machine Identity</h1>
            <p className="text-[13px] text-[#666666]">
              Zero-Trust Asymmetric Ed25519 Identity Card & Machine Credentials
            </p>
          </div>
        </div>

        {/* Agent Selector Dropdown */}
        {agents.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-bold text-[#666666]">Select Agent:</span>
            <div className="relative">
              <select
                value={selectedAgentId}
                onChange={(e) => handleSelectAgent(e.target.value)}
                className="appearance-none pl-3 pr-8 py-1.5 bg-white border border-[#E8E8E4] rounded-[8px] text-[12px] font-bold text-[#1F1F1F] focus:outline-none focus:border-[#2E9D50]"
              >
                {agents.map((ag) => (
                  <option key={ag.id} value={ag.id}>
                    {ag.name} ({ag.agent_code || "AGENT"})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#666666] absolute right-2.5 top-3 pointer-events-none" />
            </div>
          </div>
        )}
      </div>

      {loading || loadingPassport ? (
        <div className="flex items-center justify-center py-16 text-[#666666] gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-[#2E9D50]" />
          <span className="text-[14px]">Loading Cryptographic Agent Passport...</span>
        </div>
      ) : errorMsg ? (
        <div className="bg-[#FFFFFF] border border-[#E53935]/20 rounded-[12px] p-8 text-center space-y-3 max-w-lg mx-auto">
          <Bot className="w-12 h-12 text-[#E53935] mx-auto opacity-60" />
          <h3 className="text-[16px] font-bold text-[#1F1F1F]">Passport Unavailable</h3>
          <p className="text-[13px] text-[#666666]">{errorMsg}</p>
          <Link href="/agents" className="inline-block mt-2 px-4 py-2 bg-[#161C2A] text-white rounded-[6px] text-[12px] font-bold">
            Back to Agents Directory
          </Link>
        </div>
      ) : !passportData || !passportData.agent ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-4 max-w-lg mx-auto">
          <Bot className="w-12 h-12 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[18px] font-bold text-[#1F1F1F]">No Agent Passport Found</h3>
          <p className="text-[13px] text-[#666666]">
            No registered AI agents found in your organization. Register an agent in your directory to issue a cryptographic passport.
          </p>
          <Link href="/agents" className="inline-block px-4 py-2 bg-[#2E9D50] text-white rounded-[6px] text-[12px] font-bold">
            Go to AI Directory
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Cryptographic Passport Card */}
          <PassportCard
            agent={passportData.agent}
            passportNumber={passportData.passport?.passport_number || "AG-PASSPORT-000000"}
            digitalSignature={passportData.passport?.digital_signature || "ed25519:unverified"}
            algorithm={passportData.passport?.algorithm || "Ed25519"}
            keyId={passportData.passport?.key_id || "agentguard-root-ed25519-v1"}
            verificationStatus={verificationResult ? verificationResult.status : (passportData.passport?.verification_status || "VERIFIED")}
            onVerify={handleVerifySignature}
            verifying={verifying}
          />

          {/* Verification Result Notification */}
          {verificationResult && (
            <div className={`max-w-[650px] mx-auto p-4 rounded-[10px] border text-[13px] ${
              verificationResult.valid ? "bg-[#EAF7EE] border-[#2E9D50]/40 text-[#237A3C]" : "bg-[#FDECEC] border-[#E53935]/40 text-[#C62828]"
            }`}>
              <div className="flex items-center gap-2 font-bold mb-1">
                {verificationResult.valid ? "✓ Cryptographic Signature Confirmed" : "✗ Verification Alert"}
              </div>
              <p>{verificationResult.reason || (verificationResult.valid ? "Passport payload matches platform root public key." : "Failed.")}</p>
            </div>
          )}

          {/* Machine Agent Credentials Section */}
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] p-6 max-w-[650px] mx-auto space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-4">
              <div>
                <h3 className="text-[18px] font-bold text-[#1F1F1F] flex items-center gap-2">
                  <Key className="w-5 h-5 text-[#8064C8]" />
                  <span>Machine Agent Credentials</span>
                </h3>
                <p className="text-[12px] text-[#666666]">
                  Cryptographic API keys allowing this AI agent to authenticate at runtime
                </p>
              </div>
              <button
                onClick={() => { setNewKeyResult(null); setShowKeyModal(true); }}
                className="px-3 py-1.5 bg-[#8064C8] hover:bg-[#6D52B5] text-white rounded-[8px] text-[12px] font-bold flex items-center gap-1.5 transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Issue Key</span>
              </button>
            </div>

            {loadingCreds ? (
              <div className="py-6 text-center text-[#666666] text-[12px]">Loading credentials...</div>
            ) : credentials.length === 0 ? (
              <div className="py-6 text-center text-[#666666] space-y-2">
                <AlertCircle className="w-8 h-8 text-[#666666] mx-auto opacity-40" />
                <p className="text-[13px]">No machine credentials issued yet for this agent.</p>
                <p className="text-[11px] text-[#999999]">Issue a key to enable autonomous runtime execution.</p>
              </div>
            ) : (
              <div className="divide-y divide-[#E8E8E4]">
                {credentials.map((cred) => (
                  <div key={cred.id} className="py-3 flex items-center justify-between gap-4">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[13px] text-[#1F1F1F]">{cred.name || "Agent Key"}</span>
                        <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-bold ${
                          cred.status === "ACTIVE" ? "bg-[#EAF7EE] text-[#2E9D50]" : "bg-[#FDECEC] text-[#E53935]"
                        }`}>
                          {cred.status}
                        </span>
                      </div>
                      <div className="text-[11px] text-[#666666] font-mono">
                        Prefix: {cred.key_prefix} • Created: {new Date(cred.created_at).toLocaleDateString()}
                        {cred.last_used_at && ` • Last Used: ${new Date(cred.last_used_at).toLocaleDateString()}`}
                      </div>
                    </div>
                    {cred.status === "ACTIVE" && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleRotateCredential(cred.id)}
                          title="Rotate Credential"
                          className="p-1.5 text-[#666666] hover:text-[#8064C8] hover:bg-[#F1EDFA] rounded-[6px]"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleRevokeCredential(cred.id)}
                          title="Revoke Credential"
                          className="p-1.5 text-[#666666] hover:text-[#E53935] hover:bg-[#FDECEC] rounded-[6px]"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Quick Connect Integration Snippet */}
            <div className="mt-4 pt-4 border-t border-[#E8E8E4] space-y-2">
              <span className="text-[11px] font-bold text-[#666666] uppercase flex items-center gap-1">
                <Terminal className="w-3.5 h-3.5" />
                <span>Runtime Agent Authentication</span>
              </span>
              <pre className="bg-[#1F1F1F] text-[#E8E8E4] p-3 rounded-[8px] text-[11px] font-mono overflow-x-auto">
{`# 1. Exchange Agent Key for Short-Lived Machine JWT:
curl -X POST https://api.agentguard.io/api/runtime/auth \\
  -H "Content-Type: application/json" \\
  -d '{"credential": "ag_agent_...", "agent_code": "${passportData.agent.agent_code}"}'

# 2. Or authenticate directly via headers:
# X-Agent-Code: ${passportData.agent.agent_code}
# X-Agent-Key: ag_agent_...`}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Modal for Creating / Revealing Key */}
      {showKeyModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[16px] max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-[18px] font-bold text-[#1F1F1F]">
              {newKeyResult ? "Machine Credential Generated" : "Issue Machine Agent Key"}
            </h3>

            {newKeyResult ? (
              <div className="space-y-4">
                <div className="p-3 bg-[#FFF8E6] border border-[#F5A623]/40 rounded-[8px] text-[12px] text-[#8C6D1F]">
                  <strong>Warning:</strong> {newKeyResult.warning}
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#666666] uppercase">Plaintext Machine Credential</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={newKeyResult.plaintext_token}
                      className="w-full px-3 py-2 text-[12px] font-mono bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] select-all text-[#1F1F1F]"
                    />
                    <button
                      onClick={() => copyToClipboard(newKeyResult.plaintext_token)}
                      className="p-2 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] transition-colors"
                      title="Copy Key"
                    >
                      {copiedKey ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  onClick={() => setShowKeyModal(false)}
                  className="w-full py-2 bg-[#1F1F1F] text-white rounded-[8px] text-[13px] font-bold hover:bg-[#333333]"
                >
                  I Have Safely Saved This Key
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreateCredential} className="space-y-4">
                <div>
                  <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">Key Label</label>
                  <input
                    type="text"
                    required
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="e.g. Production Worker Key"
                    className="w-full px-3 py-2 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowKeyModal(false)}
                    className="px-4 py-2 border border-[#E8E8E4] text-[#666666] rounded-[8px] text-[13px] font-bold hover:bg-[#FCFCFA]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creatingKey}
                    className="px-4 py-2 bg-[#8064C8] hover:bg-[#6D52B5] text-white rounded-[8px] text-[13px] font-bold disabled:opacity-50"
                  >
                    {creatingKey ? "Generating..." : "Generate Key"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AgentPassportPage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-[#666666]">Loading Agent Passport...</div>}>
      <PassportContent />
    </Suspense>
  );
}
