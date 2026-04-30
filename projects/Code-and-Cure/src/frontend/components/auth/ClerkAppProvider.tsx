"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { ReactNode } from "react";
import ClerkTokenBridge from "./ClerkTokenBridge";

export default function ClerkAppProvider({ children }: { children: ReactNode }) {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <>{children}</>;
  }

  return (
    <ClerkProvider>
      <ClerkTokenBridge />
      {children}
    </ClerkProvider>
  );
}
