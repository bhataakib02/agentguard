"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { fetchApi } from "@/lib/api";
import { User, Mail, Lock, ArrowRight, Eye, EyeOff } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const computedOrgName = `${fullName.trim() || 'Enterprise'}'s Organization`;

    try {
      // 1. Register User in Supabase Auth
      const { data: authData, error: authErr } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
            org_name: computedOrgName,
          },
        },
      });

      if (authErr) throw new Error(authErr.message);

      const authUserId = authData.user?.id;

      // 2. Register Organization and User in FastAPI Backend
      const tokenResp = await fetchApi("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          org_name: computedOrgName,
          full_name: fullName,
          email,
          password,
          auth_user_id: authUserId,
        }),
      });

      if (tokenResp?.access_token) {
        document.cookie = `agentguard_token=${tokenResp.access_token}; path=/; max-age=86400`;
        localStorage.setItem("agentguard_token", tokenResp.access_token);
        router.push("/dashboard");
      } else {
        router.push("/login?registered=true");
      }
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[20px] sm:text-[24px] font-bold text-[#1F1F1F] tracking-tight">Register Account</h1>
        <p className="text-[12px] sm:text-[13px] text-[#666666] mt-0.5">
          Initialize your AgentGuard Runtime Control Plane workspace
        </p>
      </div>

      {error && (
        <div className="p-3 bg-[#FDECEC] border border-[#E53935]/30 rounded-[8px] text-[12px] font-bold text-[#C62828]">
          {error}
        </div>
      )}

      <form onSubmit={handleRegister} autoComplete="off" className="space-y-5">
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
          {loading ? "Creating Account..." : "Create Account"}
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>

      <div className="pt-4 border-t border-[#E8E8E4] text-center text-[12px]">
        <span className="text-[#666666]">Already registered? </span>
        <Link href="/login" className="text-[#2E9D50] font-bold hover:underline">
          Sign In
        </Link>
      </div>
    </div>
  );
}
