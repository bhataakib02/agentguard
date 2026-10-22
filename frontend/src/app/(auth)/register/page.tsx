"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { User, Mail, Lock, ArrowRight, Eye, EyeOff, KeyRound, RefreshCw, CheckCircle2 } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState<"DETAILS" | "VERIFY_OTP">("DETAILS");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
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

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const resp = await fetchApi("/auth/register/request-otp", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim().toLowerCase(),
          password,
        }),
      });

      setMessage(resp?.message || "A 6-digit verification code has been dispatched to your email address.");
      setStep("VERIFY_OTP");
      setCooldown(resp?.cooldown_seconds || 60);
    } catch (err: any) {
      setError(err?.message || "Failed to initiate registration. Please check your details and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const tokenResp = await fetchApi("/auth/register/verify-otp", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim(),
        }),
      });

      if (tokenResp?.access_token) {
        document.cookie = `agentguard_token=${tokenResp.access_token}; path=/; max-age=86400; SameSite=Lax`;
        localStorage.setItem("agentguard_token", tokenResp.access_token);
        router.push("/dashboard");
      } else {
        router.push("/login?registered=true");
      }
    } catch (err: any) {
      setError(err?.message || "Verification failed. Please check the code or request a new one.");
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
      const resp = await fetchApi("/auth/register/request-otp", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim().toLowerCase(),
          password,
        }),
      });
      setMessage(resp?.message || "A fresh 6-digit verification code has been dispatched.");
      setCooldown(resp?.cooldown_seconds || 60);
    } catch (err: any) {
      setError(err?.message || "Failed to resend verification code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[20px] sm:text-[24px] font-bold text-[#1F1F1F] tracking-tight">
          {step === "DETAILS" ? "Register Account" : "Verify Email Passcode"}
        </h1>
        <p className="text-[12px] sm:text-[13px] text-[#666666] mt-0.5">
          {step === "DETAILS"
            ? "Initialize your AgentGuard Runtime Control Plane workspace"
            : `Enter the 6-digit code sent to ${email}`}
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

      {step === "DETAILS" ? (
        <form onSubmit={handleRequestOtp} autoComplete="off" className="space-y-4">
          <div>
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1.5">
              Full Name
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
              <input
                type="text"
                required
                autoComplete="off"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
                className="w-full pl-9 pr-3 py-2.5 text-[13px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
              />
            </div>
          </div>

          <div>
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1.5">
              Work Email Address
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
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
              <input
                type={showPassword ? "text" : "password"}
                required
                minLength={6}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 6 characters"
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
            {loading ? "Sending Passcode..." : "Continue with Email Verification"}
            <ArrowRight className="w-4 h-4" />
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
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                className="w-full pl-9 pr-3 py-2 text-[14px] font-mono tracking-widest bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
              />
            </div>
            <p className="text-[11px] text-[#666666] mt-1">
              Valid for 10 minutes. Check your spam folder if not received.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || otp.length !== 6}
            className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {loading ? "Verifying..." : "Verify & Complete Registration"}
            <ArrowRight className="w-4 h-4" />
          </button>

          <div className="flex items-center justify-between pt-2 text-[11px]">
            <button
              type="button"
              onClick={() => { setStep("DETAILS"); setError(null); setMessage(null); }}
              className="text-[#666666] hover:text-[#1F1F1F] hover:underline"
            >
              ← Edit details
            </button>
            <button
              type="button"
              onClick={handleResend}
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
        <span className="text-[#666666]">Already registered? </span>
        <Link href="/login" className="text-[#2E9D50] font-bold hover:underline">
          Sign In
        </Link>
      </div>
    </div>
  );
}
