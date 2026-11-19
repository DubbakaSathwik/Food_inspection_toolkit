import { expect, test } from "@playwright/test";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { ADMIN, API, apiAs, approvedUser, completedInspection, emulatorToken, uniqueEmail } from "./helpers";

test.describe("authorization cannot be bypassed with direct API calls", () => {
  test.beforeEach(() => test.skip(test.info().project.name !== "desktop", "API-level checks run once"));

  test("no token, wrong role, other owner, role escalation", async () => {
    expect((await fetch(`${API}/api/v1/inspector/dashboard`)).status).toBe(401);
    expect((await fetch(`${API}/api/v1/admin/users`, { headers: { Authorization: "Bearer forged.token.value" } })).status).toBe(401);

    const a = uniqueEmail("owner", "api");
    const b = uniqueEmail("intruder", "api");
    await approvedUser(a);
    await approvedUser(b);
    const id = await completedInspection(a);
    for (const path of [`/api/v1/inspections/${id}`, `/api/v1/inspections/${id}/report.pdf`]) {
      expect((await apiAs(b, path)).status).toBe(404);
    }
    expect((await apiAs(b, "/api/v1/admin/users")).status).toBe(403);
    expect((await apiAs(b, "/api/v1/admin/reference", { method: "POST", body: "{}" })).status).toBe(403);
    const me = await apiAs(b, "/api/v1/me", { method: "PATCH", body: JSON.stringify({ role: "admin" }) });
    expect(me.status).toBe(422);
    const pending = uniqueEmail("pending", "api");
    const t = await emulatorToken(pending);
    await fetch(`${API}/api/v1/me`, { headers: { Authorization: `Bearer ${t}` } });
    expect((await fetch(`${API}/api/v1/inspections`, { headers: { Authorization: `Bearer ${t}` } })).status).toBe(403);
    expect((await apiAs(ADMIN, "/api/v1/admin/audit")).status).toBe(200);
    expect((await apiAs(ADMIN, "/api/v1/admin/audit", { method: "DELETE" })).status).toBe(405);
  });

  test("the static build contains no server secrets or private data", async () => {
    const files: string[] = [];
    const walk = (d: string) =>
      readdirSync(d).forEach((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : files.push(join(d, f))));
    walk(join(__dirname, "..", ".next", "static"));
    const bad =
      /mongodb(\+srv)?:\/\/|PRIVATE KEY|FIREBASE_SERVICE_ACCOUNT|GEMINI_API_KEY|NVIDIA_API_KEY|HF_API_KEY|inspector@example\.com|admin@example\.com/;
    const hits = files.filter((f) => /\.(js|css|html|json)$/.test(f) && bad.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });
});
