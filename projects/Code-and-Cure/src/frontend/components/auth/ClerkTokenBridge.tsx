"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";

import { clearStoredToken, setAccessTokenProvider, setStoredToken } from "@/lib/api";

export default function ClerkTokenBridge() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setAccessTokenProvider(null);
      clearStoredToken();
      return () => setAccessTokenProvider(null);
    }

    const resolveToken = async () => {
      const template = process.env.NEXT_PUBLIC_CLERK_TOKEN_TEMPLATE?.trim();

      if (template) {
        try {
          const templateToken = await getToken({ template });
          if (templateToken?.trim()) {
            return templateToken;
          }
        } catch {
          // Fall back to the default Clerk session token when the template is absent or invalid.
        }
      }

      return getToken();
    };

    setAccessTokenProvider(resolveToken);
    void resolveToken()
      .then((token) => setStoredToken(token))
      .catch(() => clearStoredToken());

    return () => setAccessTokenProvider(null);
  }, [getToken, isLoaded, isSignedIn]);

  return null;
}
