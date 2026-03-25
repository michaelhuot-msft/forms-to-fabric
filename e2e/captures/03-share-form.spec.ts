import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("03 — Share form and copy link", async ({ authedPage: page }) => {
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("networkidle");

  // Open the most recent form — opens in a new tab
  const [formPage] = await Promise.all([
    page.context().waitForEvent("page"),
    page.getByRole("button", { name: /Open Form of/i }).first().click(),
  ]);

  await formPage.waitForLoadState("networkidle");
  await formPage.waitForTimeout(2_000);

  // Click "Collect responses" (the share button in Forms)
  await formPage
    .getByRole("button", { name: /Collect responses/i })
    .click();
  await formPage.waitForTimeout(2_000);

  await capture(formPage, "03-share-form.png");
});
