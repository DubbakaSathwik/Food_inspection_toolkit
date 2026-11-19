"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { api, onServerState, type Page } from "@/lib/api";
import { type Area, useAuth, useGuard } from "@/lib/auth";
import { Icon, type IconName, TabIcon } from "./icon";
import type { TabIconName } from "./icon-paths";
import { initials, Logo, Pill } from "./ui";

type NavItem = { href: string; label: string; icon: IconName; badgeKey?: "proposals" };

const NAV: Record<Area, NavItem[]> = {
  inspector: [
    { href: "/inspector", label: "Dashboard", icon: "home" },
    { href: "/inspector/new", label: "New Inspection", icon: "plus" },
    { href: "/inspector/history", label: "Inspection History", icon: "history" },
    { href: "/inspector/proposals", label: "Product Proposals", icon: "proposal" },
    { href: "/inspector/ask", label: "Ask AI", icon: "chat" },
    { href: "/inspector/profile", label: "Profile", icon: "user" },
  ],
  admin: [
    { href: "/admin", label: "Dashboard", icon: "home" },
    { href: "/admin/reference", label: "Reference Database", icon: "box" },
    { href: "/admin/rules", label: "Compliance Rules", icon: "rules" },
    { href: "/admin/proposals", label: "Product Proposals", icon: "proposal", badgeKey: "proposals" },
    { href: "/admin/users", label: "User Management", icon: "users" },
    { href: "/admin/analytics", label: "Analytics", icon: "chart" },
    { href: "/admin/audit", label: "Audit Logs", icon: "logs" },
    { href: "/admin/settings", label: "Settings", icon: "settings" },
  ],
};

type Tab = { href: string; label: string; icon: TabIconName; match: (p: string) => boolean };
const TABS: Record<Area, Tab[]> = {
  inspector: [
    { href: "/inspector", label: "Home", icon: "home", match: (p) => p === "/inspector" || p.startsWith("/inspector/proposals") },
    {
      href: "/inspector/new",
      label: "Inspect",
      icon: "plus",
      match: (p) => /^\/inspector\/(new|verify|ai-review|findings|report)/.test(p),
    },
    { href: "/inspector/history", label: "History", icon: "hist", match: (p) => p.startsWith("/inspector/history") },
    { href: "/inspector/ask", label: "Ask AI", icon: "ai", match: (p) => p.startsWith("/inspector/ask") },
    { href: "/inspector/profile", label: "Profile", icon: "user", match: (p) => p.startsWith("/inspector/profile") },
  ],
  admin: [
    { href: "/admin", label: "Home", icon: "home", match: (p) => p === "/admin" },
    { href: "/admin/reference", label: "Products", icon: "box", match: (p) => p.startsWith("/admin/reference") },
    { href: "/admin/users", label: "Users", icon: "users", match: (p) => p.startsWith("/admin/users") },
    { href: "/admin/analytics", label: "Analytics", icon: "chart", match: (p) => p.startsWith("/admin/analytics") },
    { href: "/admin/settings", label: "More", icon: "menu", match: (p) => /^\/admin\/(settings|rules|proposals|audit)/.test(p) },
  ],
};

function navActive(area: Area, href: string, path: string): boolean {
  const root = area === "inspector" ? "/inspector" : "/admin";
  if (href === root) return path === root;
  if (href === "/inspector/new") return /^\/inspector\/(new|verify|ai-review|findings|report)/.test(path);
  return path === href || path.startsWith(href + "/");
}

function usePendingProposals(area: Area, enabled: boolean): number | null {
  const [n, setN] = useState<number | null>(null);
  const path = usePathname();
  useEffect(() => {
    if (area !== "admin" || !enabled) return;
    api<Page<unknown>>("/api/v1/admin/proposals", { query: { status: "pending", page_size: 1 } })
      .then((p) => setN(p.total))
      .catch(() => setN(null));
  }, [area, enabled, path]);
  return n;
}

export function AppShell({ area, children }: { area: Area; children: ReactNode }) {
  const { allowed, me } = useGuard(area);
  const { signOut } = useAuth();
  const path = usePathname();
  const pending = usePendingProposals(area, allowed);
  if (!allowed) return <FullPageLoader label="Checking your access…" />;
  const roleLabel = area === "inspector" ? "Inspector" : me?.role === "super_admin" ? "Super Admin" : "Admin";
  return (
    <>
      <header className="m-top">
        <Link href={area === "inspector" ? "/inspector" : "/admin"} className="no-underline">
          <Logo size={28} text={17} />
        </Link>
        <Pill>{roleLabel}</Pill>
      </header>
      <div className="cs-shell">
        <aside className="cs-side" aria-label="Sidebar">
          <Link href="/" className="no-underline" style={{ padding: "0 6px" }}>
            <Logo />
          </Link>
          <nav className="cs-nav" aria-label="Main">
            {NAV[area].map((item) => (
              <Link key={item.href} href={item.href} aria-current={navActive(area, item.href, path) ? "page" : undefined}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.badgeKey && pending ? (
                  <span className="badge" aria-label={`${pending} pending`}>
                    {pending}
                  </span>
                ) : null}
              </Link>
            ))}
          </nav>
          <div className="cs-foot cs-nav">
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                void signOut();
              }}
            >
              <Icon name="logout" />
              <span>Log out</span>
            </a>
          </div>
        </aside>
        <main className="cs-main" id="main">
          {children}
        </main>
      </div>
      <nav className="m-tab" aria-label="Main">
        {TABS[area].map((t) => (
          <Link key={t.href} href={t.href} aria-current={t.match(path) ? "page" : undefined}>
            <TabIcon name={t.icon} />
            {t.label}
          </Link>
        ))}
      </nav>
    </>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
  back,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  back?: ReactNode;
}) {
  const { me } = useAuth();
  const profileHref = me?.role === "inspector" ? "/inspector/profile" : "/admin/settings";
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex flex-col gap-1.5 min-w-0">
        {back}
        <h1 className="cs-h1">{title}</h1>
        {subtitle && <p className="cs-sub">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-3.5 cs-acts">
        {actions}
        <Link
          href={profileHref}
          aria-label="Account"
          title={me?.email ?? "Account"}
          className="cs-hide-sm grid place-items-center no-underline"
          style={{ width: 42, height: 42, borderRadius: 21, background: "#56703A", color: "#fff", fontWeight: 700, fontSize: 14 }}
        >
          {initials(me?.name)}
        </Link>
      </div>
    </header>
  );
}

export function FullPageLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="min-h-screen grid place-items-center" role="status" aria-live="polite">
      <div className="flex flex-col items-center gap-4">
        <div className="cs-ring" />
        <span style={{ font: "600 14px var(--font-sans)", color: "#55584E" }}>{label}</span>
      </div>
    </div>
  );
}

/** Page-to-page loader: top progress bar + overlay on internal link clicks (never calls preventDefault). */
export function RouteProgress() {
  const path = usePathname();
  const [fromPath, setFromPath] = useState<string | null>(null);
  const on = fromPath !== null && fromPath === path; // hides itself as soon as the route changes
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
      const a = (e.target as HTMLElement).closest("a");
      const href = a?.getAttribute("href");
      if (!a || !href || href.startsWith("#") || a.target === "_blank" || a.hasAttribute("download")) return;
      const u = new URL(href, location.href);
      if (u.origin !== location.origin || u.pathname === location.pathname) return;
      setFromPath(location.pathname);
      window.setTimeout(() => setFromPath(null), 1200);
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);
  return (
    <>
      <div id="cs-top" className={on ? "go" : ""} aria-hidden />
      <div id="cs-load" className={on ? "on" : ""} aria-hidden>
        <div className="cs-ring" />
        <span style={{ font: "600 14px var(--font-sans)", color: "#55584E" }}>Loading…</span>
      </div>
    </>
  );
}

/** Render free instances sleep; tell the user instead of showing errors while it wakes (NFR-05). */
export function StartingServer() {
  const [state, setState] = useState<"ok" | "waking">("ok");
  useEffect(() => onServerState(setState), []);
  if (state === "ok") return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed left-1/2 -translate-x-1/2 z-[10001] flex items-center gap-3 rounded-[12px] border border-line bg-white px-4 py-3 shadow-lg"
      style={{ top: 16, maxWidth: "calc(100vw - 32px)", fontSize: 14 }}
    >
      <span className="cs-ring" style={{ width: 20, height: 20, borderWidth: 3 }} />
      <span>
        <strong>Starting the server…</strong> The free server sleeps when idle; this can take up to a minute. Your work is safe.
      </span>
    </div>
  );
}
