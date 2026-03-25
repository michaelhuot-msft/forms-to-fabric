import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("05 — Registration flow run in Power Automate", async ({ authedPage: page }) => {
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

  await capture(page, "05-registration-flow.png");
});
