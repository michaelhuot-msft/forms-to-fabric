import { test } from "@playwright/test";
import { capture } from "../helpers";

test("03 — Share form and copy link", async ({ page }) => {
  // Navigate to the most recently created form (should be on the Forms home)
  // The user should have just created a form in step 02
  await page.goto("https://forms.office.com");
  await page.waitForLoadState("networkidle");

  // Click the most recent form to open it
  const recentForm = page
    .getByRole("link", { name: /patient satisfaction/i })
    .first();
  if (await recentForm.isVisible()) {
    await recentForm.click();
    await page.waitForLoadState("networkidle");
  }

  // Click Share button
  const shareButton = page.getByRole("button", { name: /share/i }).first();
  await shareButton.click();
  await page.waitForTimeout(2_000);

  await capture(page, "03-share-form.png");
});
