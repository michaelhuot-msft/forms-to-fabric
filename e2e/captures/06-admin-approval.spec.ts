import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

/**
 * Captures the admin approval flow where an IT admin activates
 * a form that was registered with PHI (pending_review → active).
 *
 * For non-PHI forms this step is skipped — included for completeness.
 */
test("06 — Admin approves and activates a PHI form", async ({
  authedPage: page,
}) => {
  // Navigate to Power Automate to show the admin perspective
  await page.goto(URLS.powerAutomate);
  await page.waitForLoadState("load");
  await page.waitForTimeout(5_000);

  // Navigate to My flows via the left nav
  const myFlows = page.getByRole("menuitem", { name: "My flows" });
  if (await myFlows.isVisible()) {
    await myFlows.click();
    await page.waitForLoadState("load");
    await page.waitForTimeout(3_000);
  }

  await capture(page, "06-admin-approval-flows.png");

  // Navigate to the Azure portal to show the Function App
  await page.goto("https://portal.azure.com");
  await page.waitForLoadState("load");
  await page.waitForTimeout(10_000);

  // Handle "Pick an account" if shown
  const pickAccount = page.getByRole("heading", { name: /Pick an account/i });
  if (await pickAccount.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await page.getByRole("listitem").first().click();
    await page.waitForLoadState("load");
    await page.waitForTimeout(10_000);
  }

  await capture(page, "06-admin-approval-activate.png");
});
