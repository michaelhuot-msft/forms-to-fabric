import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

/**
 * Captures the admin approval flow where an IT admin activates
 * a form that was registered with PHI (pending_review → active).
 *
 * This navigates to the Power Automate flow run history or
 * demonstrates the activation via the admin portal/API call.
 */
test("06 — Admin approves and activates a PHI form", async ({ page }) => {
  // Navigate to Power Automate to show the admin perspective
  await page.goto(URLS.powerAutomate);
  await page.waitForLoadState("networkidle");

  // Navigate to My flows to find the registration flow run
  const myFlows = page.getByRole("link", { name: /my flows/i }).first();
  if (await myFlows.isVisible()) {
    await myFlows.click();
    await page.waitForLoadState("networkidle");
  }

  await capture(page, "06-admin-approval-flows.png");

  // Show the activation step — navigate to the Function App or
  // use the admin guide's activation endpoint
  // For the screenshot, we show the flow list with the pending form
  // and the admin tools available

  // Navigate to the Azure portal Function App (activate-form endpoint)
  await page.goto(
    "https://portal.azure.com/#view/WebsitesExtension/FunctionMenuBlade"
  );
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(5_000);

  await capture(page, "06-admin-approval-activate.png");
});
