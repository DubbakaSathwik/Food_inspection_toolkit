import { expect, test } from "@playwright/test";
import { API, approvedUser, signIn, uniqueEmail } from "./helpers";

test("Ask AI: answer without and with internet research (sources shown only when switched on)", async ({ page }, info) => {
  const email = uniqueEmail("asker", info.project.name);
  await approvedUser(email);
  await signIn(page, email, "Asha Asker");
  await page.goto("/inspector/ask");
  await page.getByLabel("Your question").fill("Which declarations are mandatory on a muesli pack?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/Test provider — not a real AI answer/)).toBeVisible();
  await expect(page.getByText(/Sources \(web research/)).toHaveCount(0);
  await page.getByText(/Internet research off/).click();
  await page.getByLabel("Your question").fill("Search the FSSAI site for allergen rules");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/Sources \(web research/)).toBeVisible();
  await page.reload();
  await expect(page.getByText(/Search the FSSAI site for allergen rules/).first()).toBeVisible(); // history persisted
});

test("cold start: 'Starting the server' while the API is unreachable, then recovers", async ({ page }, info) => {
  const email = uniqueEmail("coldstart", info.project.name);
  await approvedUser(email);
  await signIn(page, email, "Cora Cold");
  await expect(page.getByRole("heading", { name: "Inspector Dashboard" })).toBeVisible();
  await page.route(`${API}/**`, (r) => r.abort("connectionrefused"));
  await page
    .getByRole("link", { name: /History/ })
    .first()
    .click();
  await expect(page.getByText("Starting the server…")).toBeVisible({ timeout: 15_000 });
  await page.unroute(`${API}/**`);
  await expect(page.getByText("Starting the server…")).toHaveCount(0, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Inspection History" })).toBeVisible();
  await expect(page.getByText(/Showing \d+ of \d+ inspections/)).toBeVisible();
});
