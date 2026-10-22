"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { fetchApi } from "@/lib/api";
import { Mail, Lock, ArrowRight, KeyRound, Eye, EyeOff, CheckCircle2, RefreshCw } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [authMode, setAuthMode] = useState<"PASSWORD" | "OTP">("PASSWORD");
  const [otpStep, setOtpStep] = useState<"REQUEST" | "VERIFY">("REQUEST");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState<number>(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (cooldown > 0) {
      timer = setTimeout(() => setCooldown((prev) => prev - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      let token: string | null = null;
      let targetRole: string | null = null;

      // 1. Attempt Supabase Auth first
      let authUserEmail = email;
      let authUserId: string | undefined = undefined;
      let supabaseSuccess = false;

      try {
        const { data, error: authErr } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (!authErr && data?.session) {
          supabaseSuccess = true;
          token = data.session.access_token;
          authUserId = data.user.id;
          authUserEmail = data.user.email || email;
          document.cookie = `agentguard_token=${data.session.access_token}; path=/; max-age=86400; SameSite=Lax`;
          localStorage.setItem("agentguard_token", data.session.access_token);
        }
      } catch (sbErr) {
        console.warn("Supabase Auth sign-in notice:", sbErr);
      }

      // 2. If Supabase Auth succeeded, sync with backend authoritative profile
      if (supabaseSuccess) {
        try {
          const backendUser = await fetchApi("/auth/login", {
            method: "POST",
            body: JSON.stringify({
              email: authUserEmail,
              auth_user_id: authUserId,
            }),
          });
          if (backendUser?.access_token) {
            token = backendUser.access_token;
            document.cookie = `agentguard_token=${backendUser.access_token}; path=/; max-age=86400; SameSite=Lax`;
            localStorage.setItem("agentguard_token", backendUser.access_token);
          }
          targetRole = backendUser?.role;
        } catch (syncErr: any) {
          console.warn("Backend auth profile sync notice:", syncErr);
        }
      } else {
        // 3. Fallback: Attempt local database login for seeded / enterprise accounts
        try {
          const localUser = await fetchApi("/auth/local-login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
          });
          if (localUser?.access_token) {
            token = localUser.access_token;
            document.cookie = `agentguard_token=${localUser.access_token}; path=/; max-age=86400; SameSite=Lax`;
            localStorage.setItem("agentguard_token", localUser.access_token);
            targetRole = localUser.role;
          }
        } catch (localErr: any) {
          console.warn("Local auth fallback notice:", localErr);
          throw new Error(localErr?.message || "Invalid email or password. Please verify your credentials.");
        }
      }

      if (!token) {
        throw new Error("Invalid email or password. Please verify your credentials.");
      }

      // 4. Authoritative routing based purely on role
      const isSuperAdmin = targetRole === "SUPER_ADMIN";
      if (isSuperAdmin) {
        router.push("/platform");
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const resp = await fetchApi("/auth/login/request-otp", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });

      setMessage(resp?.message || "If the account exists and is eligible, a 6-digit verification code has been sent.");
      setOtpStep("VERIFY");
      setCooldown(resp?.cooldown_seconds || 60);
    } catch (err: any) {
      setError(err.message || "Failed to request OTP code.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const tokenResp = await fetchApi("/auth/login/verify-otp", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otpCode.trim(),
        }),
      });

      if (!tokenResp?.access_token) {
        throw new Error("Invalid authentication response.");
      }

      document.cookie = `agentguard_token=${tokenResp.access_token}; path=/; max-age=86400; SameSite=Lax`;
      localStorage.setItem("agentguard_token", tokenResp.access_token);

      const isSuperAdmin = tokenResp.role === "SUPER_ADMIN";
      if (isSuperAdmin) {
        router.push("/platform");
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "OTP verification failed. Please check the code or request a new one.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[20px] sm:text-[24px] font-bold text-[#1F1F1F] tracking-tight">Sign In to AgentGuard</h1>
        <p className="text-[12px] sm:text-[13px] text-[#666666] mt-0.5">
          Access the Runtime Control Plane for Autonomous AI Employees
        </p>
      </div>

      {/* Auth Mode Toggle */}
      <div className="flex bg-[#FCFCFA] p-1 border border-[#E8E8E4] rounded-[8px] text-[11px] sm:text-[12px] font-bold select-none">
        <button
          type="button"
          onClick={() => { setAuthMode("PASSWORD"); setOtpStep("REQUEST"); setError(null); setMessage(null); }}
          className={`flex-1 py-1.5 px-1 text-center rounded-[6px] transition-colors ${
            authMode === "PASSWORD" ? "bg-white text-[#2E9D50] shadow-sm font-bold" : "text-[#666666]"
          }`}
        >
          Password Login
        </button>
        <button
          type="button"
          onClick={() => { setAuthMode("OTP"); setOtpStep("REQUEST"); setError(null); setMessage(null); }}
          className={`flex-1 py-1.5 px-1 text-center rounded-[6px] transition-colors ${
            authMode === "OTP" ? "bg-white text-[#2E9D50] shadow-sm font-bold" : "text-[#666666]"
          }`}
        >
          Email OTP Passcode
        </button>
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

      {authMode === "PASSWORD" ? (
        <form onSubmit={handlePasswordLogin} autoComplete="off" className="space-y-5">
          <div>
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
              <input
                type="email"
                required
                autoComplete="off"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full pl-9 pr-3 py-2.5 text-[13px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[12px] font-bold text-[#1F1F1F]">Password</label>
              <Link href="/forgot-password" className="text-[11px] text-[#2878D4] hover:underline font-bold">
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
              <input
                type={showPassword ? "text" : "password"}
                required
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-9 pr-10 py-2.5 text-[13px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 text-[#666666] hover:text-[#1F1F1F] focus:outline-none"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 mt-2"
          >
            {loading ? "Authenticating..." : "Sign In to Control Plane"}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      ) : otpStep === "REQUEST" ? (
        <form onSubmit={handleSendOtp} autoComplete="off" className="space-y-5">
          <div>
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
              <input
                type="email"
                required
                autoComplete="off"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full pl-9 pr-3 py-2.5 text-[13px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 mt-2"
          >
            {loading ? "Requesting OTP..." : "Send One-Time Passcode (OTP)"}
            <KeyRound className="w-4 h-4" />
          </button>
        </form>
      ) : (
        <form onSubmit={handleVerifyOtp} className="space-y-4">
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
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                className="w-full pl-9 pr-3 py-2 text-[14px] font-mono tracking-widest bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
              />
            </div>
            <p className="text-[11px] text-[#666666] mt-1">
              Code valid for 10 minutes.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || otpCode.length !== 6}
            className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {loading ? "Verifying..." : "Verify & Sign In"}
            <ArrowRight className="w-4 h-4" />
          </button>

          <div className="flex items-center justify-between pt-2 text-[11px]">
            <button
              type="button"
              onClick={() => { setOtpStep("REQUEST"); setError(null); setMessage(null); }}
              className="text-[#666666] hover:text-[#1F1F1F] hover:underline"
            >
              ← Change email
            </button>
            <button
              type="button"
              onClick={handleSendOtp}
              disabled={cooldown > 0 || loading}
              className="text-[#2E9D50] font-bold hover:underline disabled:text-[#999999] flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" />
              {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend Code"}
            </button>
          </div>
        </form>
      )}

      <div className="pt-4 border-t border-[#E8E8E4] text-center text-[12px]">
        <span className="text-[#666666]">Don&apos;t have an account? </span>
        <Link href="/register" className="text-[#2E9D50] font-bold hover:underline">
          Register New Account
        </Link>
      </div>
    </div>
  );
}
