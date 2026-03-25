import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("07 — Submit a response to the registered form", async ({
  authedPage: page,
}) => {
  // Navigate to Forms home and open the Patient Satisfaction Survey
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("load");
  await page.waitForTimeout(3_000);

  // Open the form — it's a button in the forms list, opens in a new tab
  const [formPage] = await Promise.all([
    page.context().waitForEvent("page"),
    page
      .getByRole("button", { name: /Open Form of Patient Satisfaction Survey/i })
      .first()
      .click(),
  ]);

  await formPage.waitForLoadState("load");
  await formPage.waitForTimeout(3_000);

  // Click Preview to see the responder view
  await formPage.getByRole("button", { name: /Preview/i }).click();
  await formPage.waitForTimeout(3_000);

  await capture(formPage, "07-submit-response-blank.png");

  // Select a radio option if available
  const firstRadio = formPage.getByRole("radio").first();
  if (await firstRadio.isVisible()) {
    await firstRadio.click();
  }

  await capture(formPage, "07-submit-response-filled.png");

  // Submit the response
  const submitButton = formPage.getByRole("button", { name: /Submit/i });
  if (await submitButton.isVisible()) {
    await submitButton.click();
    await formPage.waitForTimeout(3_000);
  }

  await capture(formPage, "07-submit-response-confirmation.png");
});
