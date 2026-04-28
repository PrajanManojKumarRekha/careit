"use client";

import { useEffect, useState } from "react";
import { api, API_BASE_URL, AuthChallengeResponse, AuthResponse } from "@/lib/api";

export type Role = "patient" | "doctor";

export interface User {
  id: string;
  name: string;
  role: Role;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.auth.me()
      .then((data) => {
        if (cancelled) return;
        setUser({
          id: data.user_id,
          name: data.role === "patient" ? "Patient" : "Doctor",
          role: data.role as Role,
        });
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const completeLogin = async (data: AuthResponse): Promise<void> => {
    const u: User = {
      id: "me",
      name: data.role === "patient" ? "Patient" : "Doctor",
      role: data.role as Role,
    };
    setUser(u);
    window.location.href = data.role === "patient" ? "/patient/dashboard" : "/doctor/dashboard";
  };

  const login = async (email: string, password: string): Promise<AuthChallengeResponse> => {
    return api.auth.login(email, password);
  };

  const verifyLogin = async (email: string, code: string, challengeId: string): Promise<void> => {
    const data = await api.auth.verifyLogin(email, code, challengeId);
    await completeLogin(data);
  };

  const register = async (
    email: string,
    password: string,
    fullName: string,
    role: Role,
  ): Promise<AuthChallengeResponse> => {
    return api.auth.register(email, password, fullName, role);
  };

  const logout = async () => {
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    }).catch(() => undefined);
    setUser(null);
    window.location.href = "/";
  };

  return { user, loading, login, verifyLogin, register, logout };
}
