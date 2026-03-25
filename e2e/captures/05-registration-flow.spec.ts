import { test } from "@playwright/test";
import { capture, URLS } from "../helpers";

test("05 — Registration flow run in Power Automate", async ({ page }) => {
  await page.goto(URLS.powerAutomate);
  await page.waitForLoadState("networkidle");

  // Navigate to My flows
  const myFlows = page.getByRole("link", { name: /my flows/i }).first();
  if (await myFlows.isVisible()) {
    await myFlows.click();
    await page.waitForLoadState("networkidle");
  }

  // Find the registration flow
  const regFlow = page
    .getByRole("link", { name: /registration intake/i })
    .first();
  if (await regFlow.isVisible()) {
    await regFlow.click();
    await page.waitForLoadState("networkidle");
  }

  await page.waitForTimeout(3_000);

  // The flow detail page shows run history
  await capture(page, "05-registration-flow.png");
});
