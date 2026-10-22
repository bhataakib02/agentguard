"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { fetchApi } from "@/lib/api";
import { KeyRound, ArrowRight, Mail, RefreshCw, CheckCircle2 } from "lucide-react";

function VerifyOtpForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState<number>(0);
  const mode = searchParams.get("mode") || "login";

  useEffect(() => {
    const queryEmail = searchParams.get("email");
    if (queryEmail) setEmail(queryEmail);
  }, [searchParams]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (cooldown > 0) {
      timer = setTimeout(() => setCooldown((prev) => prev - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    const cleanToken = token.trim();

    try {
      let authToken: string | null = null;
      let targetRole: string = "USER";

      // 1. Verify OTP with AgentGuard Backend
      const verifyEndpoint = mode === "register" ? "/auth/register/verify-otp" : "/auth/login/verify-otp";
      try {
        const resp = await fetchApi(verifyEndpoint, {
          method: "POST",
          body: JSON.stringify({
            email: cleanEmail,
            otp: cleanToken,
          }),
        });

        if (resp?.access_token) {
          authToken = resp.access_token;
          targetRole = resp.role || "USER";
        }
      } catch (backendErr: any) {
        // Fallback: Check if Supabase Auth client directly accepts the token
        try {
          const { data: sbData, error: sbErr } = await supabase.auth.verifyOtp({
            email: cleanEmail,
            token: cleanToken,
            type: "email",
          });
          if (!sbErr && sbData?.session) {
            authToken = sbData.session.access_token;
            // Sync with backend profile
            const profile = await fetchApi("/auth/login", {
              method: "POST",
              body: JSON.stringify({
                email: cleanEmail,
                auth_user_id: sbData.user?.id,
              }),
            });
            if (profile?.access_token) {
              authToken = profile.access_token;
              targetRole = profile.role || "USER";
            }
          } else {
            throw backendErr;
          }
        } catch {
          throw backendErr;
        }
      }

      if (!authToken) {
        throw new Error("Verification failed. Please ensure the passcode is correct.");
      }

      document.cookie = `agentguard_token=${authToken}; path=/; max-age=86400; SameSite=Lax`;
      localStorage.setItem("agentguard_token", authToken);

      const isSuperAdmin = targetRole === "SUPER_ADMIN";
      if (isSuperAdmin) {
        router.push("/platform");
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err?.message || "OTP verification failed. Please verify your code or request a new one.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || loading) return;
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const endpoint = mode === "register" ? "/auth/register/request-otp" : "/auth/login/request-otp";
      const resp = await fetchApi(endpoint, {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setMessage(resp?.message || "A fresh 6-digit verification code has been dispatched.");
      setCooldown(resp?.cooldown_seconds || 60);
    } catch (err: any) {
      setError(err?.message || "Failed to resend passcode.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[20px] sm:text-[24px] font-bold text-[#1F1F1F] tracking-tight">Verify Passcode</h1>
        <p className="text-[12px] sm:text-[13px] text-[#666666] mt-0.5">
          Enter the 6-digit passcode sent to <strong className="text-[#1F1F1F]">{email || "your email"}</strong>
        </p>
      </div>

      {error && (
        <div className="p-3 bg-[#FDECEC] border border-[#E53935]/30 rounded-[8px] text-[12px] font-bold text-[#C62828] leading-relaxed">
          {error}
        </div>
      )}

      {message && (
        <div className="p-3 bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-[8px] text-[12px] font-bold text-[#237A3C] leading-relaxed flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#2E9D50] shrink-0 mt-0.5" />
          <span>{message}</span>
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
            6-Digit One-Time Passcode (OTP)
          </label>
          <div className="relative">
            <KeyRound className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
            <input
              type="text"
              required
              maxLength={6}
              value={token}
              onChange={(e) => setToken(e.target.value.replace(/\D/g, ""))}
              placeholder="123456"
              className="w-full pl-9 pr-3 py-2 text-[14px] font-mono tracking-widest bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
            />
          </div>
          <p className="text-[11px] text-[#666666] mt-1">
            Valid for 10 minutes from issuance.
          </p>
        </div>

        <button
          type="submit"
          disabled={loading || token.length !== 6}
          className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
        >
          {loading ? "Verifying..." : "Verify & Sign In"}
          <ArrowRight className="w-4 h-4" />
        </button>

        <div className="flex items-center justify-between pt-2 text-[11px]">
          <Link href="/login" className="text-[#666666] hover:text-[#1F1F1F] hover:underline">
            ← Back to Login
          </Link>
          <button
            type="button"
            onClick={handleResend}
            disabled={cooldown > 0 || loading || !email}
            className="text-[#2E9D50] font-bold hover:underline disabled:text-[#999999] flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend Code"}
          </button>
        </div>
      </form>
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
