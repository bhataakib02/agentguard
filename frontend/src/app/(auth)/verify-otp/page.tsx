"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { fetchApi } from "@/lib/api";
import { KeyRound, ArrowRight, Mail } from "lucide-react";

function VerifyOtpForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const queryEmail = searchParams.get("email");
    if (queryEmail) setEmail(queryEmail);
  }, [searchParams]);

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // 1. Real Supabase Auth OTP verification (No dev fallbacks!)
      const { data, error: verifyErr } = await supabase.auth.verifyOtp({
        email,
        token,
        type: "email",
      });

      if (verifyErr) {
        if (verifyErr.message.includes("Email rate limit exceeded") || verifyErr.message.includes("Token is invalid")) {
          throw new Error("BLOCKED — email provider configuration required. Please verify SMTP settings in your Supabase dashboard or check code validity.");
        }
        throw new Error(verifyErr.message);
      }

      if (data.session) {
        document.cookie = `agentguard_token=${data.session.access_token}; path=/; max-age=86400`;
        localStorage.setItem("agentguard_token", data.session.access_token);

        await fetchApi("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: data.user?.email || email,
            auth_user_id: data.user?.id,
          }),
        });

        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    } catch (err: any) {
      setError(err.message || "OTP verification failed. Please request a new code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Verify Passcode</h1>
        <p className="text-[13px] text-[#666666]">
          Enter the 6-digit passcode sent to <strong className="text-[#1F1F1F]">{email || "your email"}</strong>
        </p>
      </div>

      {error && (
        <div className="p-3 bg-[#FDECEC] border border-[#E53935]/30 rounded-[8px] text-[12px] font-bold text-[#C62828] leading-relaxed">
          {error}
        </div>
      )}

      <form onSubmit={handleVerifyOtp} className="space-y-4">
        <div>
          <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">
            Email Address
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@enterprise.ai"
              className="w-full pl-9 pr-3 py-2 text-[13px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
            />
          </div>
        </div>

        <div>
          <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">
            One-Time Passcode (OTP)
          </label>
          <div className="relative">
            <KeyRound className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
            <input
              type="text"
              required
              maxLength={8}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="123456"
              className="w-full pl-9 pr-3 py-2 text-[13px] font-mono tracking-widest bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
        >
          {loading ? "Verifying..." : "Verify & Sign In"}
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>

      <div className="pt-4 border-t border-[#E8E8E4] text-center text-[12px]">
        <Link href="/login" className="text-[#2E9D50] font-bold hover:underline">
          Back to Login
        </Link>
      </div>
    </div>
  );
}

export default function VerifyOtpPage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-[#666666]">Loading OTP Form...</div>}>
      <VerifyOtpForm />
    </Suspense>
  );
}
