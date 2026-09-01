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
          role: (profile.email?.toLowerCase() === "thefreelancer2076@gmail.com") ? "SUPER_ADMIN" : (profile.role || "USER"),
          department: profile.department || "General",
          org_name: profile.org_name || ((profile.role === "SUPER_ADMIN" || profile.email?.toLowerCase() === "thefreelancer2076@gmail.com") ? "AgentGuard Control Plane" : "AgentGuard Enterprise"),
        };
        setUser(fullProfile);
        if (typeof window !== "undefined") {
          localStorage.setItem("agentguard_user", JSON.stringify(fullProfile));
        }
        return;
      }
    } catch (e) {
      console.warn("Backend profile sync notice:", e);
    }

    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("agentguard_user");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed && parsed.email && parsed.email.toLowerCase() === "thefreelancer2076@gmail.com") {
            parsed.role = "SUPER_ADMIN";
            parsed.full_name = "Super Admin Account";
          }
          setUser(parsed);
          return;
        } catch (err) {}
      }
    }

    if (userEmail) {
      const isSuperAdmin = userEmail.toLowerCase() === "thefreelancer2076@gmail.com";
      const nameFromEmail = isSuperAdmin ? "Super Admin Account" : userEmail.split("@")[0].replace(".", " ").toUpperCase();
      const fallbackRole = isSuperAdmin ? "SUPER_ADMIN" : "USER";
      const fallbackUser: UserProfile = {
        id: authUserId || "usr_session",
        auth_user_id: authUserId,
        email: userEmail,
        full_name: nameFromEmail,
        role: fallbackRole,
        org_name: isSuperAdmin ? "AgentGuard Control Plane" : "AgentGuard Enterprise",
      };
      setUser(fallbackUser);
    }
  };

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!mounted) return;
      setSession(session);
      if (session?.user) {
        document.cookie = `agentguard_token=${session.access_token}; path=/; max-age=86400`;
        localStorage.setItem("agentguard_token", session.access_token);
        fetchUserProfile(session.user.id, session.user.email);
      } else {
        document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        setUser(null);
      }
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (!mounted) return;
      setSession(session);

      if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED" || event === "INITIAL_SESSION") {
        if (session?.user) {
          document.cookie = `agentguard_token=${session.access_token}; path=/; max-age=86400`;
          localStorage.setItem("agentguard_token", session.access_token);
          await fetchUserProfile(session.user.id, session.user.email);
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
      await supabase.auth.signOut();
    } catch (e) {
      console.warn("Supabase signOut notice:", e);
    } finally {
      document.cookie = "agentguard_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      localStorage.removeItem("agentguard_token");
      localStorage.removeItem("agentguard_user");
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
