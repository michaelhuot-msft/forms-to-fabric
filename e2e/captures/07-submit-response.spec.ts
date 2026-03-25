import { test } from "@playwright/test";
import { capture, URLS } from "../helpers";

test("07 — Submit a response to the registered form", async ({ page }) => {
  // Navigate to Forms and open the Patient Satisfaction Survey
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("networkidle");

  // Open the form in responder view (preview)
  const recentForm = page
    .getByRole("link", { name: /patient satisfaction/i })
    .first();
  if (await recentForm.isVisible()) {
    await recentForm.click();
    await page.waitForLoadState("networkidle");
  }

  // Click Preview to see the responder view
  const previewButton = page
    .getByRole("button", { name: /preview/i })
    .first();
  if (await previewButton.isVisible()) {
    await previewButton.click();
    await page.waitForLoadState("networkidle");
  }

  await capture(page, "07-submit-response-blank.png");

  // Fill out the form with sample responses
  const firstChoice = page.getByRole("radio").first();
  if (await firstChoice.isVisible()) {
    await firstChoice.click();
  }

  // Fill any text fields
  const textFields = page.getByPlaceholder(/enter your answer/i);
  if ((await textFields.count()) > 0) {
    await textFields.first().fill("Everything was excellent, thank you!");
  }

  await capture(page, "07-submit-response-filled.png");

  // Submit the response
  const submitButton = page.getByRole("button", { name: /submit/i });
  if (await submitButton.isVisible()) {
    await submitButton.click();
    await page.waitForTimeout(3_000);
  }

  await capture(page, "07-submit-response-confirmation.png");
});
