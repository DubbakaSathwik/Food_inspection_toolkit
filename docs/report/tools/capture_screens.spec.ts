import { test } from "@playwright/test";
import { ADMIN, INSPECTOR, apiAs, signIn } from "./helpers";

const OUT = "/home/user/food_inspection_toolkit/docs/report/assets/screens";

type Insp = { id: string; status: string };

async function shot(page: import("@playwright/test").Page, dir: string, name: string, path: string, after?: () => Promise<void>) {
  try {
    await page.goto(path);
    await page.waitForTimeout(1800);
    if (after) await after();
    await page.screenshot({ path: `${OUT}/${dir}/${name}.png` });
  } catch (e) {
    console.log("SHOT FAILED", name, String(e).slice(0, 120));
  }
}

test("report screenshots", async ({ page, browser }, info) => {
  test.setTimeout(240_000);
  const dir = info.project.name === "mobile" ? "mobile" : "desktop";
  const mobile = dir === "mobile";
  const list = (await (await apiAs(INSPECTOR, "/api/v1/inspections?page_size=50")).json()) as { items: Insp[] };
  const byStatus = (s: string) => list.items.find((i) => i.status === s)?.id;
  const completed = byStatus("completed"), analysed = byStatus("analysed"), extracted = byStatus("extracted");

  // public pages (signed out)
  await shot(page, dir, "01-landing", "/");
  await shot(page, dir, "02-signin", "/signin");

  await signIn(page, INSPECTOR, "Ravi Inspector");
  await shot(page, dir, "03-inspector-dashboard", "/inspector");
  await shot(page, dir, "04-new-inspection", "/inspector/new");
  if (extracted) await shot(page, dir, "05-verify-fields", `/inspector/verify/${extracted}`);
  if (analysed) await shot(page, dir, "06-ai-review", `/inspector/ai-review/${analysed}`);
  if (analysed) await shot(page, dir, "07-findings", `/inspector/findings/${analysed}`);
  if (completed) await shot(page, dir, "08-report", `/inspector/report/${completed}`);
  await shot(page, dir, "09-history", "/inspector/history");
  await shot(page, dir, "10-ask-ai", "/inspector/ask", async () => {
    const box = page.getByRole("textbox").last();
    await box.fill("What must a packaged food label show?");
    await box.press("Enter");
    await page.waitForTimeout(2500);
  });

  // admin pages
  await page.evaluate(() => window.localStorage.clear()).catch(() => undefined);
  await signIn(page, ADMIN, "Asha Admin");
  await shot(page, dir, "11-admin-dashboard", "/admin");
  await shot(page, dir, "12-reference-database", "/admin/reference");
  await shot(page, dir, "13-compliance-rules", "/admin/rules");
  await shot(page, dir, "14-proposals", "/admin/proposals");
  await shot(page, dir, "15-users", "/admin/users");
  await shot(page, dir, "16-analytics", "/admin/analytics");
  await shot(page, dir, "17-audit-logs", "/admin/audit");
  await shot(page, dir, "18-diagnostics", "/admin/diagnostics", async () => {
    await page.getByRole("button", { name: "Run all checks" }).click();
    await page.waitForTimeout(3500);
  });
  await shot(page, dir, "19-settings", "/admin/settings");
  void browser; void mobile;
});
