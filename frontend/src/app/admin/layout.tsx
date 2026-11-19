"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AppShell area="admin">{children}</AppShell>;
}
