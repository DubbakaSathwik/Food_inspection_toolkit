import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { ADMIN, apiAs, signIn } from "./helpers";

test.beforeEach(async ({ page }) => {
  await signIn(page, ADMIN, "Asha Admin");
});

test("analytics: period filter and chart table view", async ({ page }) => {
  await page.goto("/admin/analytics");
  await expect(page.getByText(/Inspections \(30 days\)/)).toBeVisible();
  await page.getByLabel("Period").selectOption("7");
  await expect(page.getByText(/Inspections \(7 days\)/)).toBeVisible();
  await page.getByRole("button", { name: "Show table" }).click();
  await expect(page.getByRole("cell", { name: /^W\d+$/ }).first()).toBeVisible(); // table rows (headers are hidden on mobile by design)
  await page.getByRole("button", { name: "Show chart" }).click();
  await expect(page.getByText(/Database storage \(Atlas free tier\)/)).toBeVisible();
});

test("audit logs: action filter, search, change details and CSV export", async ({ page }) => {
  const code = `DR-AU-${String(Date.now()).slice(-6)}`;
  const r = await apiAs(ADMIN, "/api/v1/admin/rules", {
    method: "POST",
    body: JSON.stringify({
      code,
      title: "Audit trail rule",
      category: "all",
      check_type: "required_field",
      field: "batch",
      requirement: "Batch required",
    }),
  });
  expect(r.status).toBe(201);
  const id = ((await r.json()) as { id: string }).id;
  await apiAs(ADMIN, `/api/v1/admin/rules/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ severity: "high", change_note: "audit e2e" }),
  });

  await page.goto("/admin/audit");
  await page.getByLabel("Action").selectOption("rule.");
  await page.getByLabel("Search").fill(code);
  const row = page.getByRole("row").filter({ hasText: `Rule ${code} v2` });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /1 field/ }).click();
  await expect(page.getByRole("cell", { name: "severity", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: '"high"', exact: true })).toBeVisible();
  const [csv] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export CSV" }).click()]);
  const text = readFileSync((await csv.path())!).toString();
  expect(text).toContain(code);
  expect(text).not.toContain("user.approve"); // export respects the action filter
});
