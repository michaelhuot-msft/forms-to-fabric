import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("08 — Per-form data flow run in Power Automate", async ({ authedPage: page }) => {
  await page.goto(URLS.powerAutomate);
  await page.waitForLoadState("networkidle");

  // Navigate to My flows
  const myFlows = page.getByRole("link", { name: /my flows/i }).first();
  if (await myFlows.isVisible()) {
    await myFlows.click();
    await page.waitForLoadState("networkidle");
  }

  // Find the per-form data processing flow
  const dataFlow = page
    .getByRole("link", { name: /patient satisfaction/i })
    .first();
  if (await dataFlow.isVisible()) {
    await dataFlow.click();
    await page.waitForLoadState("networkidle");
  }

  await page.waitForTimeout(3_000);

  // The flow detail page shows run history with the successful run
  await capture(page, "08-data-flow.png");
});
