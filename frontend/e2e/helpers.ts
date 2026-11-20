import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";

export const API = process.env.E2E_API_URL ?? "http://localhost:8000";
const EMU = process.env.E2E_AUTH_EMULATOR ?? "http://127.0.0.1:9099";

/** Emulator Google sign-in from Node; same subject as the in-browser test helper (sub-<email>). */
export async function emulatorToken(email: string, name = "Test User"): Promise<string> {
  const idToken = JSON.stringify({ sub: `sub-${email}`, email, email_verified: true, name });
  const r = await fetch(`${EMU}/identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=demo-api-key`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      postBody: `id_token=${idToken}&providerId=google.com`,
      requestUri: "http://localhost",
      returnSecureToken: true,
    }),
  });
  const j = (await r.json()) as { idToken: string };
  return j.idToken;
}

export async function apiAs(email: string, path: string, init: RequestInit = {}, name?: string): Promise<Response> {
  const t = await emulatorToken(email, name);
  return fetch(API + path, {
    ...init,
    headers: { ...(init.headers ?? {}), Authorization: `Bearer ${t}`, "content-type": "application/json" },
  });
}

export const ADMIN = "admin@example.com"; // SUPER_ADMIN_EMAIL in the test backend
export const INSPECTOR = "inspector@example.com";

/** Ensure the super admin and an approved inspector exist (idempotent). */
export async function seedUsers(): Promise<void> {
  await apiAs(ADMIN, "/api/v1/me", {}, "Asha Admin");
  const me = (await (await apiAs(INSPECTOR, "/api/v1/me", {}, "Ravi Inspector")).json()) as { uid: string; status: string };
  if (me.status !== "active") {
    await apiAs(ADMIN, `/api/v1/admin/users/${me.uid}/approve`, { method: "POST", body: JSON.stringify({ role: "inspector" }) });
  }
}

export async function signIn(page: Page, email: string, name = "Test User"): Promise<void> {
  await page.goto("/signin");
  await page.waitForFunction(() => typeof (window as unknown as { __csTestSignIn?: unknown }).__csTestSignIn === "function");
  await page.evaluate(
    ([e, n]) => (window as unknown as { __csTestSignIn: (a: string, b: string) => Promise<void> }).__csTestSignIn(e, n),
    [email, name],
  );
  await page.waitForURL((u) => !u.pathname.startsWith("/signin"), { timeout: 20000 });
}

export const FIXTURES = join(__dirname, "fixtures");
export const fixture = (name: string) => join(FIXTURES, name);

/** A unique email per test run and project, so journeys never share state. */
export function uniqueEmail(prefix: string, project: string): string {
  return `${prefix}-${project}-${Date.now()}-${Math.floor(Math.random() * 1e4)}@example.com`;
}

/** Create (via the API) a user with an approved role. Returns their uid. */
export async function approvedUser(email: string, role: "inspector" | "admin" = "inspector", name = "E2E User"): Promise<string> {
  const me = (await (await apiAs(email, "/api/v1/me", {}, name)).json()) as { uid: string };
  const r = await apiAs(ADMIN, `/api/v1/admin/users/${me.uid}/approve`, { method: "POST", body: JSON.stringify({ role }) });
  if (!r.ok) throw new Error(`approve failed ${r.status} ${await r.text()}`);
  return me.uid;
}

async function call(email: string, path: string, init: RequestInit = {}): Promise<Response> {
  const t = await emulatorToken(email);
  return fetch(API + path, { ...init, headers: { ...(init.headers ?? {}), Authorization: `Bearer ${t}` } });
}

/** Build a completed inspection (with report) through the API — used as a starting point for proposal journeys. */
export async function completedInspection(email: string): Promise<string> {
  const json = { "content-type": "application/json" };
  const id = ((await (await call(email, "/api/v1/inspections", { method: "POST" })).json()) as { id: string }).id;
  await call(email, `/api/v1/inspections/${id}/category`, { method: "PUT", headers: json, body: JSON.stringify({ category: "staples" }) });
  for (const [file, label] of [
    ["front.png", "front"],
    ["back.png", "back"],
  ]) {
    const fd = new FormData();
    fd.append("file", new Blob([readFileSync(fixture(file))], { type: "image/png" }), file);
    fd.append("label", label);
    const r = await call(email, `/api/v1/inspections/${id}/photos`, { method: "POST", body: fd });
    if (!r.ok) throw new Error(`upload ${r.status}`);
  }
  for (const [path, body] of [
    [`/extract`, undefined],
    [`/fields/confirm`, { keys: [] }],
    [`/analyze`, undefined],
  ] as const) {
    const r = await call(email, `/api/v1/inspections/${id}${path}`, {
      method: "POST",
      headers: json,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) throw new Error(`${path} ${r.status}`);
  }
  await call(email, `/api/v1/inspections/${id}/decision`, {
    method: "PUT",
    headers: json,
    body: JSON.stringify({ classification: "not_verified", remarks: "" }),
  });
  const r = await call(email, `/api/v1/inspections/${id}/report`, {
    method: "POST",
    headers: json,
    body: JSON.stringify({ signature_name: "E2E", confirm_reviewed: true }),
  });
  if (!r.ok) throw new Error(`report ${r.status}`);
  return id;
}

/** Waits until React has attached to the photo input. Setting files before hydration loses the change event (flaky on slow CI). */
export async function fileInputReady(page: import("@playwright/test").Page): Promise<void> {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="file"][multiple]');
    return !!el && Object.keys(el).some((k) => k.startsWith("__reactProps"));
  });
}
