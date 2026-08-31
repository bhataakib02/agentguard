"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import PassportCard from "@/components/ui/PassportCard";
import { ArrowLeft, Bot } from "lucide-react";

function PassportContent() {
  const searchParams = useSearchParams();
  const agentId = searchParams.get("id") || "";
  const [passportData, setPassportData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPassport() {
      try {
        setLoading(true);
        const endpoint = agentId ? `/agents/${agentId}/passport` : `/agents/first/passport`;
        const res = await fetchApi(endpoint).catch(() => null);
        setPassportData(res);
      } catch (err) {
        console.error("Passport fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadPassport();
  }, [agentId]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-5">
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
      </div>

      {loading ? (
        <div className="text-center py-12 text-[#666666]">Loading Agent Passport...</div>
      ) : !passportData || !passportData.agent ? (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-12 text-center space-y-4 max-w-lg mx-auto">
          <Bot className="w-12 h-12 text-[#666666] mx-auto opacity-40" />
          <h3 className="text-[18px] font-bold text-[#1F1F1F]">No Passport Found</h3>
          <p className="text-[13px] text-[#666666]">
            No registered AI agent passport was found in the database. Please create an AI agent in the directory to issue a cryptographic passport.
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
