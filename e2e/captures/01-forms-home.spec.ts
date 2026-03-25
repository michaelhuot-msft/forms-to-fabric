import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("01 — Forms home page", async ({ authedPage: page }) => {
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("networkidle");

  await capture(page, "01-forms-home.png");
});
