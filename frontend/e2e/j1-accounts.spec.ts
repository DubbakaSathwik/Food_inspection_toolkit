import { expect, test } from "@playwright/test";
import { ADMIN, apiAs, approvedUser, signIn, uniqueEmail } from "./helpers";

test.describe("accounts", () => {
  test("new Google sign-in waits on Pending until an admin approves it in the UI", async ({ browser }, info) => {
    const email = uniqueEmail("newbie", info.project.name);
    const inspector = await (await browser.newContext()).newPage();
    await signIn(inspector, email, "Nina Newbie");
    await expect(inspector).toHaveURL(/\/pending/);
    await expect(inspector.getByRole("heading", { name: "Your account is awaiting approval" })).toBeVisible();
    await expect(inspector.getByText(email)).toBeVisible();

    const admin = await (await browser.newContext()).newPage();
    await signIn(admin, ADMIN, "Asha Admin");
    await admin.goto("/admin/users");
    const row = admin
      .locator("div")
      .filter({ hasText: email })
      .filter({ has: admin.getByRole("button", { name: "Approve" }) })
      .last();
    await row.getByRole("button", { name: "Approve" }).click();
    await expect(admin.getByText(`${email} approved as Inspector`)).toBeVisible();

    await inspector.getByRole("button", { name: "Check again" }).click();
    await expect(inspector).toHaveURL(/\/inspector$/);
    await expect(inspector.getByRole("heading", { name: "Inspector Dashboard" })).toBeVisible();
  });

  test("disabling an account takes effect in an open session", async ({ page }, info) => {
    const email = uniqueEmail("tobedisabled", info.project.name);
    const uid = await approvedUser(email);
    await signIn(page, email, "Dee Disabled");
    await expect(page.getByRole("heading", { name: "Inspector Dashboard" })).toBeVisible();
    const r = await apiAs(ADMIN, `/api/v1/admin/users/${uid}`, { method: "PATCH", body: JSON.stringify({ status: "disabled" }) });
    expect(r.ok).toBe(true);
    // In the open session (no reload): the next API call is refused and the app moves to the "disabled" screen.
    await page
      .getByRole("link", { name: /History/ })
      .first()
      .click();
    await expect(page.getByRole("heading", { name: "Your account is disabled" })).toBeVisible({ timeout: 20_000 });
    // After a full reload the revoked session cannot be refreshed: the user is signed out, and signing in again
    // still lands on the "disabled" screen.
    await page.goto("/inspector/history");
    await expect(page).toHaveURL(/\/(pending|signin)/, { timeout: 20_000 });
    if (page.url().includes("/signin")) await signIn(page, email, "Dee Disabled");
    await expect(page.getByRole("heading", { name: "Your account is disabled" })).toBeVisible({ timeout: 20_000 });
  });

  test("demoting an admin moves an open session out of the admin area", async ({ page }, info) => {
    const email = uniqueEmail("demoted", info.project.name);
    const uid = await approvedUser(email, "admin");
    await signIn(page, email, "Dan Demoted");
    await expect(page.getByRole("heading", { name: "Admin Dashboard" })).toBeVisible();
    const r = await apiAs(ADMIN, `/api/v1/admin/users/${uid}`, { method: "PATCH", body: JSON.stringify({ role: "inspector" }) });
    expect(r.ok).toBe(true);
    await page.goto("/admin/users");
    await expect(page).toHaveURL(/\/inspector$/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { name: "Inspector Dashboard" })).toBeVisible();
  });
});
