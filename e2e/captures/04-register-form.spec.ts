import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

/**
 * This step opens the self-service "Register Your Form for Analytics"
 * registration form and captures screenshots of it.
 *
 * The registration form asks 3 questions:
 * 1. Paste your form's share link
 * 2. Give your form a short name
 * 3. Does this form collect any patient information? (Yes/No)
 */
test("04 — Register form via self-service registration", async ({
  authedPage: page,
}) => {
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("load");
  await page.waitForTimeout(3_000);

  // Open the registration form — opens in a new tab
  const [formPage] = await Promise.all([
    page.context().waitForEvent("page"),
    page
      .getByRole("button", { name: /Register Your Form for Analytics/i })
      .first()
      .click(),
  ]);

  await formPage.waitForLoadState("load");
  await formPage.waitForTimeout(3_000);

  // Dismiss any "Got it" banner if present
  const gotIt = formPage.getByRole("button", { name: "Got it" });
  if (await gotIt.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await gotIt.click();
  }

  // Click Preview to see the responder view
  await formPage.getByRole("button", { name: /Preview/i }).click();
  await formPage.waitForTimeout(3_000);

  await capture(formPage, "04-register-form-blank.png");

  // Fill in text fields
  const shareLink = formPage.getByRole("textbox", {
    name: /Paste your form's share link/i,
  });
  if (await shareLink.isVisible()) {
    await shareLink.fill(
      "https://forms.office.com/Pages/ResponsePage.aspx?id=example-patient-survey"
    );
  }

  const formName = formPage.getByRole("textbox", {
    name: /Give your form a short name/i,
  });
  if (await formName.isVisible()) {
    await formName.fill("Patient Satisfaction Survey");
  }

  // Select "No" for the PHI question
  const noRadio = formPage.getByRole("radio", { name: "No" });
  if (await noRadio.isVisible()) {
    await noRadio.click();
  }

  await capture(formPage, "04-register-form-filled.png");

  // Submit the form
  const submitButton = formPage.getByRole("button", { name: /Submit/i });
  if (await submitButton.isVisible()) {
    await submitButton.click();
    await formPage.waitForTimeout(3_000);
  }

  await capture(formPage, "04-register-form-confirmation.png");
});
