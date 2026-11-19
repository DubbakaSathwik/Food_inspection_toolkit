import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { ADMIN, fixture, signIn } from "./helpers";

test.beforeEach(async ({ page }) => {
  await signIn(page, ADMIN, "Asha Admin");
});

test("reference record: manual entry, packaging version + photo, archive and restore", async ({ page }, info) => {
  const name = `E2E Oat Biscuits ${info.project.name} ${Date.now()}`;
  await page.goto("/admin/reference");
  await page.getByRole("button", { name: "Add Product" }).click();
  await page.getByRole("button", { name: /Manual entry/ }).click();
  const dlg = page.getByRole("dialog", { name: "Add product — manual entry" });
  await dlg.getByLabel("Product name *").fill(name);
  await dlg.getByLabel("Brand *").fill("Testbrand");
  await dlg.getByLabel("Category *").selectOption("snacks");
  await dlg.getByLabel(/Licence \/ registration no/).fill("123");
  await dlg.getByRole("button", { name: "Save record" }).click();
  await expect(dlg.getByText(/14 digits/).first()).toBeVisible(); // server-side validation shown next to the field
  await dlg.getByLabel(/Licence \/ registration no/).fill("11122233344455");
  await dlg.getByRole("button", { name: "Save record" }).click();
  await expect(page).toHaveURL(/\/admin\/reference\/REF-\d+/);
  await expect(page.getByRole("heading", { name })).toBeVisible();

  await page.getByRole("button", { name: "Add version" }).click();
  await page.getByLabel("Version label").fill("2026-A");
  await page.getByRole("dialog").getByRole("button", { name: "Add version" }).click();
  await expect(page.getByText("Version 2026-A")).toBeVisible();
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Add image" }).click();
  await (await chooser).setFiles(fixture("reference.png"));
  await expect(page.getByRole("img", { name: /front · version 2026-A/ })).toBeVisible({ timeout: 20_000 });

  await page.getByRole("button", { name: "Archive record" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Archived", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Restore record" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Active", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Added .*Oat Biscuits/).first()).toBeVisible(); // record history from the audit log
});

test("reference: AI-assisted draft and CSV import with validation preview", async ({ page }, info) => {
  await page.goto("/admin/reference");
  await page.getByRole("button", { name: "Add Product" }).click();
  await page.getByRole("button", { name: /AI-assisted entry/ }).click();
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Choose photographs" }).click();
  await (await chooser).setFiles(fixture("front.png"));
  await page.getByRole("button", { name: "Draft record" }).click();
  const manual = page.getByRole("dialog", { name: "Add product — manual entry" });
  await expect(manual.getByLabel("Brand *")).toHaveValue("Harvest Lane"); // drafted, not saved
  await manual.getByRole("button", { name: "Cancel" }).click();

  const name = `Imported Tea ${info.project.name} ${Date.now()}`;
  mkdirSync(test.info().outputDir, { recursive: true });
  const csv = join(test.info().outputDir, "import.csv");
  writeFileSync(
    csv,
    `product_name,brand,category,net_quantity,licence_number\n${name},Leafy,beverages,250 g,10012022009999\nBad Row,,snacks,,123\n`,
  );
  await page.getByRole("button", { name: "Add Product" }).click();
  await page.getByRole("button", { name: /Excel \/ CSV import/ }).click();
  const fc = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: /Choose \.csv or \.xlsx file/ }).click();
  await (await fc).setFiles(csv);
  await expect(page.getByText(/1\s*valid ·/)).toBeVisible();
  await page.getByRole("button", { name: "Import 1 valid row" }).click();
  await expect(page.getByText("Imported 1 record.")).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();
  await page.getByLabel("Search").fill(name);
  await expect(page.getByRole("row").filter({ hasText: name })).toBeVisible();
});

test("compliance rule: create, edit (new version) and history", async ({ page }, info) => {
  const code = `DR-E2${info.project.name === "mobile" ? "M" : "D"}-${String(Date.now()).slice(-5)}`;
  await page.goto("/admin/rules");
  await page.getByRole("button", { name: "Add Rule" }).click();
  const dlg = page.getByRole("dialog", { name: "Add rule" });
  await dlg.getByLabel("Rule ID").fill(code);
  await dlg.getByLabel("Rule name").fill("E2E batch rule");
  await dlg.getByLabel("Field checked").selectOption("batch");
  await dlg.getByLabel("Requirement").fill("Batch number must be printed.");
  await dlg.getByRole("button", { name: "Create rule" }).click();
  await page.getByLabel("Search").fill(code);
  const row = page.getByRole("row").filter({ hasText: code });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: `Edit ${code}` }).click();
  const edit = page.getByRole("dialog", { name: "Edit rule" });
  await edit.getByLabel("Severity").selectOption("high");
  await edit.getByLabel(/Change note/).fill("Stricter after review");
  await edit.getByRole("button", { name: "Save new version" }).click();
  await page
    .getByRole("row")
    .filter({ hasText: code })
    .getByRole("button", { name: `View ${code}` })
    .click();
  await expect(page.getByText(/v2 · Stricter after review/)).toBeVisible();
});

test("website image upload is shown on the public landing page, then reset", async ({ page, browser }) => {
  await page.goto("/admin/settings");
  const chooser = page.waitForEvent("filechooser");
  await page
    .getByRole("button", { name: /Upload image|Replace image/ })
    .first()
    .click();
  await (await chooser).setFiles(fixture("reference.png"));
  await expect(page.getByText("Image uploaded. It is now shown on the site.")).toBeVisible();
  const visitor = await (await browser.newContext()).newPage();
  await visitor.goto("/");
  await expect(visitor.locator('img[src*="/api/v1/public/site-images/hero"]')).toBeVisible();
  await page.getByRole("button", { name: "Reset to placeholder" }).first().click();
  await expect(page.getByText("Reset to the labelled placeholder.")).toBeVisible();
});
