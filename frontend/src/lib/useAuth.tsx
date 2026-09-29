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
        const fullProfile: UserProfile = {
          id: profile.id,
          auth_user_id: profile.auth_user_id || authUserId,
          email: profile.email,
          full_name: profile.full_name,
          role: profile.role || "USER",
          department: profile.department || "General",
          org_name: profile.org_name || (profile.role === "SUPER_ADMIN" ? "AgentGuard Control Plane" : "AgentGuard Enterprise"),
        };
        setUser(fullProfile);
        return;
      }
    } catch (e) {
      console.warn("Backend profile sync notice:", e);
    }

    // No valid backend profile found: unauthenticated
    setUser(null);
  };

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!mounted) return;
      setSession(session);
      if (session?.user) {
        document.cookie = `agentguard_token=${session.access_token}; path=/; max-age=86400; SameSite=Lax`;
        localStorage.setItem("agentguard_token", session.access_token);
        await fetchUserProfile(session.user.id, session.user.email);
      } else {
        document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        localStorage.removeItem("agentguard_token");
        localStorage.removeItem("agentguard_user");
        setUser(null);
      }
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (!mounted) return;
      setSession(session);

      if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED" || event === "INITIAL_SESSION") {
        if (session?.user) {
          document.cookie = `agentguard_token=${session.access_token}; path=/; max-age=86400; SameSite=Lax`;
          localStorage.setItem("agentguard_token", session.access_token);
          await fetchUserProfile(session.user.id, session.user.email);
        } else {
          document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
          localStorage.removeItem("agentguard_token");
          localStorage.removeItem("agentguard_user");
          setUser(null);
        }
      } else if (event === "SIGNED_OUT") {
        document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        localStorage.removeItem("agentguard_token");
        localStorage.removeItem("agentguard_user");
        setUser(null);
      }
      setLoading(false);
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
