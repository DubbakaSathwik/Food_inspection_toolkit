"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";

export default function InspectorLayout({ children }: { children: ReactNode }) {
  return <AppShell area="inspector">{children}</AppShell>;
}
