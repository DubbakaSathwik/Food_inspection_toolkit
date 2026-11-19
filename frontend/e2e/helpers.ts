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
