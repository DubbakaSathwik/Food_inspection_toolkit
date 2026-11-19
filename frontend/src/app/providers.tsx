"use client";

import { type ReactNode, useEffect } from "react";
import { RouteProgress, StartingServer } from "@/components/shell";
import { warmUp } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    void warmUp(); // wake a sleeping backend (Render free) before the user needs it
  }, []);
  return (
    <AuthProvider>
      <RouteProgress />
      <StartingServer />
      {children}
    </AuthProvider>
  );
}
