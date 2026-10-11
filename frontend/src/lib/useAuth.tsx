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

  const fetchUserProfile = async (authUserId?: string, userEmail?: string) => {
    try {
      const profile = await fetchApi("/auth/me");
      if (profile && profile.email) {
        const isSuperAdminEmail = profile.email?.toLowerCase() === "thefreelancer2076@gmail.com";
        const authoritativeRole = isSuperAdminEmail ? "SUPER_ADMIN" : (profile.role || "USER");
        const fullProfile: UserProfile = {
          id: profile.id,
          auth_user_id: profile.auth_user_id || authUserId,
          email: profile.email,
          full_name: profile.full_name,
          role: authoritativeRole,
          department: profile.department || "General",
          org_name: profile.org_name || (authoritativeRole === "SUPER_ADMIN" ? "Platform Admin Control" : "AgentGuard Enterprise"),
        };
        setUser(fullProfile);
        return;
      }
    } catch (e) {
      console.warn("Backend profile sync notice:", e);
    }
  };

  useEffect(() => {
    let mounted = true;

    const applySession = async (currentSession: any) => {
      if (!mounted) return;
      setSession(currentSession);
      if (currentSession?.user) {
        document.cookie = `agentguard_token=${currentSession.access_token}; path=/; max-age=86400; SameSite=Lax`;
        localStorage.setItem("agentguard_token", currentSession.access_token);

        const isSuperAdminEmail = currentSession.user.email?.toLowerCase() === "thefreelancer2076@gmail.com";
        const initialRole = isSuperAdminEmail
          ? "SUPER_ADMIN"
          : (currentSession.user.app_metadata?.role || currentSession.user.user_metadata?.role || "USER");

        setUser((prev) => prev || {
          id: currentSession.user.id,
          auth_user_id: currentSession.user.id,
          email: currentSession.user.email || "",
          full_name: currentSession.user.user_metadata?.full_name || (initialRole === "SUPER_ADMIN" ? "Platform Super Admin" : "User"),
          role: initialRole,
          department: "General",
          org_name: initialRole === "SUPER_ADMIN" ? "Platform Admin Control" : "AgentGuard Enterprise",
        });

        await fetchUserProfile(currentSession.user.id, currentSession.user.email);
      } else {
        document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        localStorage.removeItem("agentguard_token");
        localStorage.removeItem("agentguard_user");
        setUser(null);
      }
      setLoading(false);
    };

    supabase.auth.getSession().then(({ data: { session } }) => {
      applySession(session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED" || event === "INITIAL_SESSION") {
        applySession(session);
      } else if (event === "SIGNED_OUT") {
        document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        localStorage.removeItem("agentguard_token");
        localStorage.removeItem("agentguard_user");
        setUser(null);
        setLoading(false);
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
      document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      localStorage.removeItem("agentguard_token");
      localStorage.removeItem("agentguard_user");
      localStorage.removeItem("agentguard_selected_org_id");
      setUser(null);
      setSession(null);
      setLoading(false);

      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
  };

  const refreshProfile = async () => {
    if (session?.user) {
      await fetchUserProfile(session.user.id, session.user.email);
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
