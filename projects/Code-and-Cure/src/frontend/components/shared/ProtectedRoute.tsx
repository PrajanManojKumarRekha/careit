"use client";

import { useAuth } from "@/hooks/useAuth";
import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ProtectedRoute({
  children,
  role,
}: {
  children: ReactNode;
  role: "patient" | "doctor";
}) {
  const router = useRouter();
  const { user, loading, error } = useAuth();

  useEffect(() => {
    if (loading) return;
    if (error) return;
    if (!user || user.role !== role) {
      router.replace("/");
    }
  }, [error, loading, role, router, user]);

  if (loading) return null;
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 text-center">
        <div className="max-w-lg rounded-3xl border border-error/20 bg-error-container px-6 py-5 text-error shadow-xl">
          {error}
        </div>
      </div>
    );
  }
  if (!user || user.role !== role) return null;

  return <>{children}</>;
}
