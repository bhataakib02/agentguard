"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import PassportCard from "@/components/ui/PassportCard";
import { ArrowLeft, Bot, RefreshCw, ChevronDown } from "lucide-react";

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

  // 1. Fetch available tenant agents
  useEffect(() => {
    async function loadTenantAgents() {
      setLoading(true);
      setErrorMsg(null);
      try {
        const agentList = await fetchApi("/agents").catch(() => []);
        const validAgents = Array.isArray(agentList) ? agentList : [];
        setAgents(validAgents);

        // If an initialAgentId was supplied in the URL, verify or use it
        if (initialAgentId) {
          setSelectedAgentId(initialAgentId);
        } else if (validAgents.length > 0) {
          // Default to the first agent owned by the caller's organization
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

  // 2. Fetch specific agent passport when selectedAgentId changes
  useEffect(() => {
    if (!selectedAgentId) {
      setPassportData(null);
      return;
    }

    async function loadPassport() {
      setLoadingPassport(true);
      setErrorMsg(null);
      try {
        const res = await fetchApi(`/agents/${selectedAgentId}/passport`);
        setPassportData(res);
      } catch (err: any) {
        console.error("Passport fetch error:", err);
        setErrorMsg(err.message || "Unable to retrieve cryptographic passport for this agent.");
        setPassportData(null);
      } finally {
        setLoadingPassport(false);
      }
    }

    loadPassport();
  }, [selectedAgentId]);

  const handleSelectAgent = (newId: string) => {
    setSelectedAgentId(newId);
    router.replace(`/agents/passport?id=${newId}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E8E8E4] pb-5">
        <div className="flex items-center gap-3">
          <Link href="/agents" className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] hover:bg-[#FCFCFA]">
            <ArrowLeft className="w-4 h-4 text-[#666666]" />
          </Link>
          <div>
            <h1 className="text-[24px] font-bold text-[#1F1F1F]">Cryptographic Agent Passport</h1>
            <p className="text-[13px] text-[#666666]">
              Zero-Trust Cryptographic Identity Verification Card
            </p>
          </div>
        </div>

        {/* Agent Selector Dropdown (if multiple agents exist in tenant org) */}
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
            No registered AI agents found in your organization. Please register an agent in your organization directory to issue and view a cryptographic passport.
          </p>
          <Link href="/agents" className="inline-block px-4 py-2 bg-[#2E9D50] text-white rounded-[6px] text-[12px] font-bold">
            Go to AI Directory
          </Link>
        </div>
      ) : (
        <PassportCard
          agent={passportData.agent}
          passportNumber={passportData.passport?.passport_number || "AG-PASSPORT-000000"}
          digitalSignature={passportData.passport?.digital_signature || "sha256:unverified"}
        />
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
