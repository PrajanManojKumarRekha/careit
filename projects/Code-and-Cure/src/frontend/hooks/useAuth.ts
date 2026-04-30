"use client";

import { useAuth as useClerkAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";

import { api, clearStoredToken, getStoredToken } from "@/lib/api";

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
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return useTokenOnlyAuth();
  }

  return useCombinedAuth();
}

function useTokenOnlyAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getStoredToken()
      .then((token) => {
        if (!token) {
          if (!cancelled) {
            setUser(null);
            setError(null);
            setLoading(false);
          }
          return null;
        }
        return api.auth.me();
      })
      .then((data) => {
        if (!data || cancelled) return;
        setUser(mapSessionUser(data));
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
  }, []);

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // Best effort only.
    }
    clearStoredToken();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.assign("/");
    }
  };

  return { user, loading, error, isLoaded: true, isSignedIn: Boolean(user), logout };
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

      const stored = await getStoredToken();
      if (!stored) {
        return null;
      }
      const data = await api.auth.me();
      return mapSessionUser(data);
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
