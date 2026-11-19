import { expect, type Page, test } from "@playwright/test";
import { ADMIN, API, INSPECTOR, apiAs, seedUsers, signIn } from "./helpers";

/** Phase 2 visual sweep: every route renders at 1440 and 390 without horizontal overflow or console errors. */
type Item = { id: string; status: string };
let ids: Record<string, string> = {};

test.beforeAll(async () => {
  await seedUsers();
  const r = await apiAs(INSPECTOR, "/api/v1/inspections?page_size=100");
  const items = ((await r.json()) as { items: Item[] }).items;
  for (const s of ["draft", "extracted", "analysed", "completed"]) {
    const hit = items.find((i) => i.status === s);
    if (hit) ids[s] = hit.id;
  }
  ids = { ...ids, ref: "REF-0001" };
});

async function check(page: Page, path: string, name: string) {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    // 404/409 are expected API answers on some screens; apis.google.com (Firebase redirect helper preloaded on mobile
    // user agents) is unreachable from the sandboxed test network — an environment limit, not an app error.
    if (m.type() === "error" && !/status of (404|409)|ERR_TUNNEL_CONNECTION_FAILED/.test(m.text())) errors.push(m.text());
  });
  await page.goto(path);
  await page.waitForLoadState("load");
  // Firebase keeps a connection open, so "networkidle" never settles: wait for loaders to finish instead.
  await expect(page.locator(".cs-skel:visible, .cs-ring:visible")).toHaveCount(0, { timeout: 20_000 });
  await page.waitForTimeout(400);
  await expect(page.locator("main, #main").first()).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, `${path} horizontal overflow`).toBeLessThanOrEqual(0);
  await page.screenshot({ path: `test-results/screens/${test.info().project.name}/${name}.png`, fullPage: true, animations: "disabled" });
  expect(errors, `${path} console errors`).toEqual([]);
}

test("public pages", async ({ page }) => {
  await check(page, "/", "Main");
  await check(page, "/signin", "SignIn");
});

test("pending page", async ({ page }) => {
  await apiAs("pending.person@example.com", "/api/v1/me", {}, "Priya Pending");
  await signIn(page, "pending.person@example.com", "Priya Pending");
  await expect(page).toHaveURL(/\/pending/);
  await check(page, "/pending", "Pending");
});

test("inspector screens", async ({ page }) => {
  await signIn(page, INSPECTOR, "Ravi Inspector");
  const routes: [string, string][] = [
    ["/inspector", "InspectorDashboard"],
    ["/inspector/new" + (ids.draft ? `?id=${ids.draft}` : ""), "NewInspection"],
    ...(ids.extracted ? ([[`/inspector/verify/${ids.extracted}`, "VerifyFields"]] as [string, string][]) : []),
    ...(ids.analysed ? ([[`/inspector/findings/${ids.analysed}`, "InspectionResults"]] as [string, string][]) : []),
    ...(ids.completed ? ([[`/inspector/report/${ids.completed}`, "ReportPreview"]] as [string, string][]) : []),
    ["/inspector/history", "InspectionHistory"],
    ["/inspector/proposals", "InspectorProposals"],
    ["/inspector/ask", "AskAI"],
    ["/inspector/profile", "Profile"],
  ];
  for (const [p, n] of routes) await check(page, p, n);
  if (ids.extracted) await check(page, `/inspector/ai-review/${ids.extracted}`, "AIReview");
});

test("admin screens", async ({ page }) => {
  await signIn(page, ADMIN, "Asha Admin");
  for (const [p, n] of [
    ["/admin", "AdminDashboard"],
    ["/admin/reference", "ReferenceDatabase"],
    [`/admin/reference/${ids.ref}`, "ProductDetail"],
    ["/admin/rules", "ComplianceRules"],
    ["/admin/proposals", "AdminProposals"],
    ["/admin/users", "UserManagement"],
    ["/admin/analytics", "Analytics"],
    ["/admin/audit", "AuditLogs"],
    ["/admin/settings", "Settings"],
  ])
    await check(page, p, n);
});

test("backend reachable", async () => {
  expect((await fetch(`${API}/health`)).ok).toBe(true);
});
