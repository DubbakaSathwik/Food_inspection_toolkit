"use client";

import { env } from "./env";
import { getFirebaseAuth } from "./firebase";
import type { components } from "./api-types";

export type S = components["schemas"];
export type Me = S["MeOut"];
export type Inspection = S["InspectionOut"];
export type InspectionSummary = S["InspectionSummary"];
export type Field = S["FieldOut"];
export type Finding = S["FindingOut"];
export type Photo = S["PhotoOut"];
export type Proposal = S["ProposalOut"];
export type Reference = S["ReferenceOut"];
export type Rule = S["RuleOut"];
export type AdminUser = S["UserAdminOut"];
export type ChatMessage = S["ChatMessageOut"];
export type SettingsOut = S["SettingsOut"];
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields?: Record<string, string>,
  ) {
    super(message);
  }
}

/* ---------------------------------------------------------------- server wake-up (Render cold start) */
type ServerState = "ok" | "waking";
let serverState: ServerState = "ok";
const listeners = new Set<(s: ServerState) => void>();
export function onServerState(fn: (s: ServerState) => void): () => void {
  listeners.add(fn);
  fn(serverState);
  return () => listeners.delete(fn);
}
function setServerState(s: ServerState) {
  if (s !== serverState) {
    serverState = s;
    listeners.forEach((l) => l(s));
  }
}
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Warm the backend as early as possible; resolves when /health answers (or after ~2 minutes). */
export async function warmUp(): Promise<boolean> {
  for (let i = 0; i < 24; i++) {
    try {
      const r = await fetch(`${env.apiBase}/health`, { cache: "no-store" });
      if (r.ok) {
        setServerState("ok");
        return true;
      }
    } catch {
      /* network error while the host wakes */
    }
    setServerState("waking");
    await sleep(Math.min(1000 * 2 ** Math.min(i, 3), 8000));
  }
  return false;
}

/* ---------------------------------------------------------------- auth events */
const authListeners = new Set<(code: string) => void>();
export function onAuthProblem(fn: (code: string) => void): () => void {
  authListeners.add(fn);
  return () => authListeners.delete(fn);
}

async function token(force = false): Promise<string | null> {
  const user = getFirebaseAuth()?.currentUser;
  return user ? user.getIdToken(force) : null;
}

type Opts = {
  method?: string;
  body?: unknown;
  form?: FormData;
  query?: Record<string, string | number | boolean | undefined | null>;
  auth?: boolean;
};

function url(path: string, query?: Opts["query"]): string {
  const u = new URL(env.apiBase + path);
  for (const [k, v] of Object.entries(query ?? {})) if (v !== undefined && v !== null && v !== "") u.searchParams.set(k, String(v));
  return u.toString();
}

async function send(path: string, o: Opts, forceRefresh = false): Promise<Response> {
  const headers: Record<string, string> = {};
  if (o.auth !== false) {
    const t = await token(forceRefresh);
    if (t) headers.Authorization = `Bearer ${t}`;
  }
  let body: BodyInit | undefined;
  if (o.form) body = o.form;
  else if (o.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(o.body);
  }
  for (let attempt = 0; ; attempt++) {
    try {
      const r = await fetch(url(path, o.query), { method: o.method ?? "GET", headers, body, cache: "no-store" });
      const isJson = (r.headers.get("content-type") ?? "").includes("json");
      if ([502, 503, 504].includes(r.status) && !isJson && attempt < 8) {
        setServerState("waking");
        await sleep(Math.min(2000 * (attempt + 1), 10000));
        continue;
      }
      setServerState("ok");
      return r;
    } catch (e) {
      if (attempt >= 8) throw new ApiError(0, "network_error", "Cannot reach the server. Check your connection.");
      setServerState("waking");
      await sleep(Math.min(2000 * (attempt + 1), 10000));
      void e;
    }
  }
}

async function raise(r: Response): Promise<never> {
  let code = "error";
  let message = `Request failed (${r.status}).`;
  let fields: Record<string, string> | undefined;
  try {
    const j = (await r.json()) as { error?: { code: string; message: string; fields?: Record<string, string> } };
    if (j.error) ({ code, message, fields } = j.error);
  } catch {
    /* non-JSON error body */
  }
  if (r.status === 401 || code.startsWith("account_")) authListeners.forEach((l) => l(code));
  throw new ApiError(r.status, code, message, fields);
}

async function request(path: string, o: Opts = {}): Promise<Response> {
  let r = await send(path, o);
  if (r.status === 401) {
    const peek = (await r
      .clone()
      .json()
      .catch(() => ({}))) as { error?: { code?: string } };
    if (peek.error?.code === "claims_stale" || peek.error?.code === "unauthenticated") {
      r = await send(path, o, true); // refresh the ID token once (new custom claims) and retry
    }
  }
  if (!r.ok) await raise(r);
  return r;
}

export async function api<T>(path: string, o: Opts = {}): Promise<T> {
  const r = await request(path, o);
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

/** Authenticated binary download (inspection photos, PDFs) — returns a Blob. */
export async function apiBlob(path: string, o: Opts = {}): Promise<Blob> {
  return (await request(path, o)).blob();
}

export function publicUrl(path: string): string {
  return env.apiBase + path;
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Something went wrong.";
}
