"use client";

import React, { useEffect, useState, createContext, useContext } from "react";
import { supabase } from "@/lib/supabase";
import { fetchApi } from "@/lib/api";

export interface UserProfile {
  id: string;
  auth_user_id?: string;
  email: string;
  full_name: string;
  role: string;
  department?: string;
  org_name?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  session: any | null;
  loading: boolean;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
  logout: async () => {},
  refreshProfile: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<any | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const clearSession = () => {
    document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    localStorage.removeItem("agentguard_token");
    localStorage.removeItem("agentguard_user");
    localStorage.removeItem("agentguard_selected_org_id");
    setUser(null);
    setSession(null);
    setLoading(false);
  };

  const validateAndApplyBackendSession = async (token: string): Promise<boolean> => {
    try {
      const profile = await fetchApi("/auth/me");
      if (profile && profile.id && profile.email) {
        const authoritativeRole = profile.role || "USER";
        const fullProfile: UserProfile = {
          id: profile.id,
          auth_user_id: profile.auth_user_id,
          email: profile.email,
          full_name: profile.full_name,
          role: authoritativeRole,
          department: profile.department || "General",
          org_name: profile.org_name || (authoritativeRole === "SUPER_ADMIN" ? "Platform Admin Control" : "AgentGuard Enterprise"),
        };
        setUser(fullProfile);
        setSession({
          access_token: token,
          user: {
            id: profile.id,
            email: profile.email,
            user_metadata: { full_name: profile.full_name },
            app_metadata: { role: authoritativeRole },
          },
        });
        document.cookie = `agentguard_token=${token}; path=/; max-age=86400; SameSite=Lax`;
        localStorage.setItem("agentguard_token", token);
        setLoading(false);
        return true;
      }
    } catch (err) {
      console.warn("Backend session validation notice:", err);
    }
    clearSession();
    return false;
  };

  useEffect(() => {
    let mounted = true;

    const initializeAuth = async () => {
      try {
        // 1. Check Supabase session first
        const { data: { session: sbSession } } = await supabase.auth.getSession();
        if (!mounted) return;

        if (sbSession?.user) {
          setSession(sbSession);
          document.cookie = `agentguard_token=${sbSession.access_token}; path=/; max-age=86400; SameSite=Lax`;
          localStorage.setItem("agentguard_token", sbSession.access_token);
          await validateAndApplyBackendSession(sbSession.access_token);
          return;
        }

        // 2. If no Supabase session, check AGENTGUARD token (e.g. from passwordless OTP login)
        const localToken = typeof window !== "undefined" ? localStorage.getItem("agentguard_token") : null;
        if (localToken) {
          const isValid = await validateAndApplyBackendSession(localToken);
          if (!isValid && mounted) {
            clearSession();
          }
        } else {
          if (mounted) clearSession();
        }
      } catch (e) {
        console.warn("Auth initialization notice:", e);
        if (mounted) clearSession();
      }
    };

    initializeAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, sbSession) => {
      if (!mounted) return;
      if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
        if (sbSession?.user) {
          setSession(sbSession);
          document.cookie = `agentguard_token=${sbSession.access_token}; path=/; max-age=86400; SameSite=Lax`;
          localStorage.setItem("agentguard_token", sbSession.access_token);
          await validateAndApplyBackendSession(sbSession.access_token);
        }
      } else if (event === "SIGNED_OUT") {
        // Check if an independent AGENTGUARD token exists before wiping
        const localToken = typeof window !== "undefined" ? localStorage.getItem("agentguard_token") : null;
        if (localToken) {
          const valid = await validateAndApplyBackendSession(localToken);
          if (!valid && mounted) clearSession();
        } else {
          if (mounted) clearSession();
        }
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const logout = async () => {
    setLoading(true);
    try {
      await fetchApi("/auth/logout", { method: "POST" }).catch(() => {});
      await supabase.auth.signOut();
    } catch (e) {
      console.warn("Sign out notice:", e);
    } finally {
      clearSession();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
  };

  const refreshProfile = async () => {
    const localToken = typeof window !== "undefined" ? localStorage.getItem("agentguard_token") : null;
    if (localToken) {
      await validateAndApplyBackendSession(localToken);
    }
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, logout, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
