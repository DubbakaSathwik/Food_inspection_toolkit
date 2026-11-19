import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { approvedUser, fixture, signIn, uniqueEmail } from "./helpers";

test("full inspection: photos → crop → AI reading → corrections → AI review → findings → decision → report → PDF → note", async ({
  page,
  browser,
}, info) => {
  test.setTimeout(180_000);
  const email = uniqueEmail("inspector", info.project.name);
  await approvedUser(email, "inspector", "Ravi Journey");
  await signIn(page, email, "Ravi Journey");

  // Step 1 — photographs
  await page.goto("/inspector/new");
  await page.getByRole("radio", { name: "Groceries & Food Staples" }).click();
  await expect(page).toHaveURL(/\/inspector\/new\?id=CS-/);
  const id = new URL(page.url()).searchParams.get("id")!;
  await page.locator('input[type="file"][multiple]').setInputFiles([fixture("front.png"), fixture("back.png"), fixture("blurry.png")]);
  await expect(page.getByText("3 of 5 added")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/Issue found in Photo 3/)).toBeVisible();

  await page.getByRole("option", { name: /Photo 1/ }).click();
  await page.getByRole("button", { name: "Crop" }).click();
  const img = page.getByRole("img", { name: "Photograph to crop" });
  await expect(img).toBeVisible();
  const box = (await img.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.15, box.y + box.height * 0.1);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.85, box.y + box.height * 0.9, { steps: 6 });
  await page.mouse.up();
  await page.getByRole("button", { name: "Save crop" }).click();
  await expect(page.getByText(/Cropped area will be used for analysis/)).toBeVisible();

  // Step 2 — AI reading + field review
  await page.getByRole("button", { name: "Extract Label Information" }).click();
  await expect(page).toHaveURL(new RegExp(`/inspector/verify/${id}`));
  await expect(page.getByRole("heading", { name: "Check what was read from the label" })).toBeVisible({ timeout: 60_000 });
  const mfg = page.getByRole("article", { name: "Manufacturing date" });
  await mfg.getByRole("button", { name: "Fix value" }).click();
  await mfg.getByRole("textbox").fill("12/09/2025");
  await mfg.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("article", { name: "Manufacturing date" }).getByText("Corrected by you")).toBeVisible();
  await expect(page.getByRole("article", { name: "Manufacturing date" }).getByText("12/09/2026")).toBeVisible(); // original AI value kept
  await page.getByRole("button", { name: "Confirm all remaining" }).click();
  await expect(page.getByText(/22 of 22 fields checked/)).toBeVisible();

  // Step 3 — AI review (animation holds until the real analysis returns)
  await page.getByRole("button", { name: "Continue to AI Review" }).click();
  await expect(page).toHaveURL(new RegExp(`/inspector/findings/${id}`), { timeout: 60_000 });

  // Step 4 — findings and decision
  const allergen = page.getByRole("article", { name: "Allergen declaration" });
  await allergen.getByRole("button", { name: "Confirm issue" }).click();
  await expect(allergen.getByText("Confirm issue")).toBeVisible();
  const claim = page.getByRole("article", { name: "Health and nutrition claims" });
  await claim.getByRole("button", { name: "Not an issue" }).click();
  await claim.getByRole("textbox", { name: "Reason" }).fill("Claim substantiated on the back panel");
  await claim.getByRole("button", { name: "Not an issue" }).click();
  await expect(
    page.getByRole("article", { name: "Health and nutrition claims" }).getByText(/Your comment: Claim substantiated/),
  ).toBeVisible();
  await page.getByRole("radio", { name: /Not verified/ }).check();
  await page.getByLabel("Remarks").fill("Allergen declaration missing on pack.");
  await page.getByRole("button", { name: "Continue to report" }).click();

  // Step 5 — report
  await expect(page).toHaveURL(new RegExp(`/inspector/report/${id}`));
  await page.getByRole("checkbox", { name: /I have reviewed the findings/ }).check();
  await page.getByRole("button", { name: "Save Report" }).click();
  await expect(page.getByText("Report saved")).toBeVisible({ timeout: 60_000 });
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
  expect(download.suggestedFilename()).toBe(`${id}.pdf`);
  const pdf = readFileSync((await download.path())!);
  expect(pdf.subarray(0, 4).toString()).toBe("%PDF");
  expect(pdf.length).toBeGreaterThan(20_000);

  await page.getByLabel("Add a note").fill("Follow-up: sample sent to the laboratory.");
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("Follow-up: sample sent to the laboratory.")).toBeVisible();

  // History, filters and exports
  await page.goto("/inspector/history");
  await page.getByRole("button", { name: /^Not verified/ }).click();
  const row = page.getByRole("row").filter({ hasText: id });
  await expect(row).toBeVisible();
  await expect(row.getByText("Not verified")).toBeVisible();
  const [csv] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export CSV" }).click()]);
  expect(readFileSync((await csv.path())!).toString()).toContain(id);
  const [xlsx] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export Excel" }).click()]);
  expect(xlsx.suggestedFilename()).toBe("inspection-history.xlsx");

  // Isolation through the UI: another inspector cannot open this inspection
  const other = uniqueEmail("other", info.project.name);
  await approvedUser(other);
  const page2 = await (await browser.newContext()).newPage();
  await signIn(page2, other, "Olga Other");
  for (const path of [`/inspector/findings/${id}`, `/inspector/report/${id}`, `/inspector/verify/${id}`]) {
    await page2.goto(path);
    await expect(page2.getByText("Inspection not found.")).toBeVisible();
  }
});

test("AI provider outage: inspection saved as incomplete, then retried successfully", async ({ page }, info) => {
  test.setTimeout(120_000);
  const email = uniqueEmail("outage", info.project.name);
  await approvedUser(email);
  await signIn(page, email, "Omar Outage");
  await page.goto("/inspector/new");
  await page.locator('input[type="file"][multiple]').setInputFiles([fixture("fail.png")]);
  await expect(page.getByText("1 of 5 added")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Extract Label Information" }).click();
  await expect(page.getByRole("heading", { name: "The AI could not read the label" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/simulated provider failure/).first()).toBeVisible();

  await page.goto("/inspector");
  await expect(page.getByText("AI reading failed").first()).toBeVisible();

  await page
    .getByRole("link", { name: /Retry AI reading/ })
    .first()
    .click();
  await page.getByRole("button", { name: "Change photographs" }).click();
  await page.getByRole("button", { name: "Replace" }).click();
  await page.locator('input[type="file"][multiple]').setInputFiles([fixture("front.png")]);
  await expect(page.getByText("1 of 5 added")).toBeVisible();
  await expect(page.getByText(/Clear and readable/)).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Extract Label Information" }).click();
  await expect(page.getByRole("heading", { name: "Check what was read from the label" })).toBeVisible({ timeout: 60_000 });
});
