import { expect, test } from "@playwright/test";
import { ADMIN, approvedUser, completedInspection, signIn, uniqueEmail } from "./helpers";

test("proposal: inspector submits → admin requests info → inspector replies → admin approves → new demo reference record", async ({
  browser,
}, info) => {
  test.setTimeout(150_000);
  const email = uniqueEmail("proposer", info.project.name);
  await approvedUser(email, "inspector", "Priya Proposer");
  const id = await completedInspection(email);
  const productName = `Ragi Flour ${info.project.name} ${Date.now()}`;

  const insp = await (await browser.newContext()).newPage();
  await signIn(insp, email, "Priya Proposer");
  await insp.goto(`/inspector/report/${id}`);
  await insp.getByRole("button", { name: "Submit as proposal" }).click();
  const dialog = insp.getByRole("dialog", { name: "Submit product proposal" });
  await dialog.getByLabel("Product name").fill(productName);
  await dialog.getByLabel("Remarks for the administrator").fill("Not in the reference database.");
  await dialog.getByRole("button", { name: "Submit proposal" }).click();
  const submitted = insp.getByText(/Proposal PR-\d{4}-\d{4,} was submitted/);
  await expect(submitted).toBeVisible();
  const pid = (await submitted.textContent())!.match(/PR-\d{4}-\d{4,}/)![0];

  const admin = await (await browser.newContext()).newPage();
  await signIn(admin, ADMIN, "Asha Admin");
  await admin.goto(`/admin/proposals?open=${pid}`);
  await expect(admin.getByRole("heading", { name: `Reviewing: ${productName}` })).toBeVisible();
  await admin.getByLabel(/Note to the inspector/).fill("Please add a clearer photo of the licence panel.");
  await admin.getByRole("button", { name: "Request information" }).click();
  await expect(admin.getByText(`Proposal ${pid} marked info requested.`)).toBeVisible();

  await insp.goto("/inspector/proposals");
  const row = insp.getByRole("row").filter({ hasText: pid });
  await expect(row.getByText("Info requested")).toBeVisible();
  await row.getByRole("button", { name: "View" }).click();
  await expect(insp.getByText(/Please add a clearer photo of the licence panel/).first()).toBeVisible();
  await insp.getByLabel("Reply to the administrator").fill("Licence panel is visible on photo 2 of the report.");
  await insp.getByRole("button", { name: "Send reply" }).click();
  await expect(insp.getByRole("row").filter({ hasText: pid }).getByText("Pending")).toBeVisible();

  await admin.goto(`/admin/proposals?open=${pid}`);
  await expect(admin.getByText(/Licence panel is visible on photo 2/).first()).toBeVisible();
  await admin.getByRole("button", { name: "Approve" }).click();
  const done = admin.getByText(/Approved — demo reference record REF-\d+ created\./);
  await expect(done).toBeVisible();
  const ref = (await done.textContent())!.match(/REF-\d+/)![0];

  await admin.goto("/admin/reference");
  await admin.getByLabel("Search").fill(productName);
  await expect(admin.getByRole("row").filter({ hasText: productName })).toBeVisible();
  await admin.goto(`/admin/reference/${ref}`);
  await expect(admin.getByRole("heading", { name: productName })).toBeVisible();
  await expect(admin.getByText("Proposal", { exact: true })).toBeVisible(); // source
});
