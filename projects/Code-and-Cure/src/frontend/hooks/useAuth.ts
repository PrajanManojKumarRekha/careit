"use client";

import { useAuth as useClerkAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

import { api, clearStoredToken } from "@/lib/api";

export type Role = "patient" | "doctor";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
}

export function useAuth() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return {
      user: null,
      loading: false,
      error: "Clerk is not configured. Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY to enable authentication.",
      isLoaded: true,
      isSignedIn: false,
      logout: async () => undefined,
    };
  }

  return useConfiguredAuth();
}

function useConfiguredAuth() {
  const { isLoaded, isSignedIn, signOut } = useClerkAuth();
  const { user: clerkUser } = useUser();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      setUser(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    api.auth
      .syncSession()
      .then((data) => {
        if (cancelled) return;
        setUser({
          id: data.user_id || clerkUser?.id || "me",
          name: data.full_name || clerkUser?.fullName || "careIT User",
          email: data.email || clerkUser?.primaryEmailAddress?.emailAddress || "",
          role: data.role as Role,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setUser(null);
        setError(err instanceof Error ? err.message : "Authentication failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [clerkUser?.fullName, clerkUser?.id, clerkUser?.primaryEmailAddress?.emailAddress, isLoaded, isSignedIn]);

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // Clerk session invalidation is the source of truth, so backend logout is best-effort.
    }
    clearStoredToken();
    await signOut({ redirectUrl: "/" });
    setUser(null);
  };

  return { user, loading, error, isLoaded, isSignedIn, logout };
}
