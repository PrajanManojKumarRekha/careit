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

function mapSessionUser(data: {
  user_id?: string;
  full_name?: string;
  email?: string;
  role: string;
}, fallback?: {
  id?: string;
  fullName?: string | null;
  email?: string | null;
}): User {
  return {
    id: data.user_id || fallback?.id || "me",
    name: data.full_name || fallback?.fullName || "careIT User",
    email: data.email || fallback?.email || "",
    role: data.role as Role,
  };
}

export function useAuth() {
  return useCombinedAuth();
}

function useCombinedAuth() {
  const { isLoaded, isSignedIn, signOut } = useClerkAuth();
  const { user: clerkUser } = useUser();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    const loadSession = async () => {
      if (isSignedIn) {
        const data = await api.auth.syncSession();
        return mapSessionUser(data, {
          id: clerkUser?.id,
          fullName: clerkUser?.fullName,
          email: clerkUser?.primaryEmailAddress?.emailAddress || null,
        });
      }

      return null;
    };

    loadSession()
      .then((resolvedUser) => {
        if (cancelled) return;
        setUser(resolvedUser);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        clearStoredToken();
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
      // Clerk session invalidation is the source of truth when present.
    }
    clearStoredToken();
    if (isSignedIn) {
      await signOut({ redirectUrl: "/" });
      return;
    }
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.assign("/");
    }
  };

  return { user, loading, error, isLoaded, isSignedIn: isSignedIn || Boolean(user), logout };
}
