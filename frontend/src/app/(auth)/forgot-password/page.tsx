"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { Mail, Lock, ArrowRight, KeyRound, Eye, EyeOff, CheckCircle2, RefreshCw } from "lucide-react";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<"REQUEST" | "RESET" | "COMPLETE">("REQUEST");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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
      const resp = await fetchApi("/auth/forgot-password/request-otp", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });

      setMessage(resp?.message || "If the account exists and is eligible, a 6-digit recovery code has been sent.");
      setStep("RESET");
      setCooldown(resp?.cooldown_seconds || 60);
    } catch (err: any) {
      setError(err?.message || "Failed to process recovery request.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const resp = await fetchApi("/auth/forgot-password/reset", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim(),
          new_password: newPassword,
        }),
      });

      setMessage(resp?.message || "Password has been successfully updated. All active sessions have been revoked.");
      setStep("COMPLETE");
    } catch (err: any) {
      setError(err?.message || "Failed to reset password. Please verify the code and try again.");
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
      const resp = await fetchApi("/auth/forgot-password/request-otp", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      setMessage(resp?.message || "A fresh recovery code has been dispatched.");
      setCooldown(resp?.cooldown_seconds || 60);
    } catch (err: any) {
      setError(err?.message || "Failed to resend recovery code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[20px] sm:text-[24px] font-bold text-[#1F1F1F] tracking-tight">
          {step === "COMPLETE" ? "Password Reset Complete" : "Reset Password"}
        </h1>
        <p className="text-[12px] sm:text-[13px] text-[#666666] mt-0.5">
          {step === "REQUEST" && "Enter your email address to receive a secure 6-digit recovery code"}
          {step === "RESET" && `Enter the 6-digit recovery code sent to ${email} and choose a new password`}
          {step === "COMPLETE" && "Your password has been changed. You may now sign in."}
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

      {step === "REQUEST" && (
        <form onSubmit={handleRequestOtp} className="space-y-4">
          <div>
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">
              Work Email Address
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

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {loading ? "Sending Code..." : "Send Recovery Code"}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      )}

      {step === "RESET" && (
        <form onSubmit={handleResetPassword} className="space-y-4">
          <div>
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">
              6-Digit Recovery Passcode
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
              Passcode expires in 10 minutes.
            </p>
          </div>

          <div>
            <label className="block text-[12px] font-bold text-[#1F1F1F] mb-1">
              New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-[#666666] absolute left-3 top-3" />
              <input
                type={showPassword ? "text" : "password"}
                required
                minLength={6}
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Minimum 6 characters"
                className="w-full pl-9 pr-10 py-2 text-[13px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-[#666666] hover:text-[#1F1F1F] focus:outline-none"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || otp.length !== 6 || newPassword.length < 6}
            className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {loading ? "Resetting Password..." : "Set New Password & Revoke Sessions"}
            <ArrowRight className="w-4 h-4" />
          </button>

          <div className="flex items-center justify-between pt-2 text-[11px]">
            <button
              type="button"
              onClick={() => { setStep("REQUEST"); setError(null); setMessage(null); }}
              className="text-[#666666] hover:text-[#1F1F1F] hover:underline"
            >
              ← Change email
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

      {step === "COMPLETE" && (
        <div className="space-y-4 pt-2">
          <p className="text-[13px] text-[#333333] leading-relaxed">
            Your credentials have been securely updated. To protect your account, all prior active sessions across all devices have been terminated.
          </p>
          <Link
            href="/login"
            className="w-full py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center justify-center gap-2 transition-colors"
          >
            Sign In with New Password
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {step !== "COMPLETE" && (
        <div className="pt-4 border-t border-[#E8E8E4] text-center text-[12px]">
          <Link href="/login" className="text-[#2E9D50] font-bold hover:underline">
            Back to Login
          </Link>
        </div>
      )}
    </div>
  );
}
