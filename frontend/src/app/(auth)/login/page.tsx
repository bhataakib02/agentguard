"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { fetchApi } from "@/lib/api";
import { Mail, Lock, ArrowRight, KeyRound, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [authMode, setAuthMode] = useState<"PASSWORD" | "OTP">("PASSWORD");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      // 1. Supabase Auth Sign In
      const { data, error: authErr } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authErr) throw new Error(authErr.message);

      if (data.session) {
        document.cookie = `agentguard_token=${data.session.access_token}; path=/; max-age=86400`;
        localStorage.setItem("agentguard_token", data.session.access_token);

        // 2. Sync user profile with FastAPI backend
        await fetchApi("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: data.user.email,
            auth_user_id: data.user.id,
          }),
        });

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
      const { error: otpErr } = await supabase.auth.signInWithOtp({
        email,
        options: {
          shouldCreateUser: true,
        },
      });

      if (otpErr) {
        if (otpErr.message.includes("Email rate limit exceeded") || otpErr.message.includes("Error sending magic link")) {
          throw new Error("BLOCKED — email provider configuration required. SMTP service is not currently configured in the Supabase dashboard.");
        }
        throw new Error(otpErr.message);
      }

      setMessage("One-Time Passcode (OTP) sent to your email. Please check your inbox.");
      router.push(`/verify-otp?email=${encodeURIComponent(email)}`);
    } catch (err: any) {
      setError(err.message || "Failed to send OTP code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">Sign In to AgentGuard</h1>
        <p className="text-[13px] text-[#666666]">
          Access the Runtime Control Plane for Autonomous AI Employees
        </p>
      </div>

      {/* Auth Mode Toggle */}
      <div className="flex bg-[#FCFCFA] p-1 border border-[#E8E8E4] rounded-[8px] text-[12px] font-bold">
        <button
          type="button"
          onClick={() => { setAuthMode("PASSWORD"); setError(null); setMessage(null); }}
          className={`flex-1 py-1.5 rounded-[6px] transition-colors ${
            authMode === "PASSWORD" ? "bg-white text-[#2E9D50] shadow-sm" : "text-[#666666]"
          }`}
        >
          Password Login
        </button>
        <button
          type="button"
          onClick={() => { setAuthMode("OTP"); setError(null); setMessage(null); }}
          className={`flex-1 py-1.5 rounded-[6px] transition-colors ${
            authMode === "OTP" ? "bg-white text-[#2E9D50] shadow-sm" : "text-[#666666]"
          }`}
        >
          Email OTP Passcode
        </button>
      </div>

      {error && (
        <div className="p-3 bg-[#FDECEC] border border-[#E53935]/30 rounded-[8px] text-[12px] font-bold text-[#C62828]">
          {error}
        </div>
      )}

      {message && (
        <div className="p-3 bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-[8px] text-[12px] font-bold text-[#237A3C]">
          {message}
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
      ) : (
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
