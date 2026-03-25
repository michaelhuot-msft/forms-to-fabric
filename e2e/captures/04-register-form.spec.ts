import { test } from "@playwright/test";
import { capture, URLS } from "../helpers";

/**
 * This step opens the self-service "Register Your Form for Analytics"
 * registration form and submits the newly created form for registration.
 *
 * The registration form asks 3 questions:
 * 1. Paste your form's share link
 * 2. Give your form a short name
 * 3. Does this form collect any patient information? (Yes/No)
 */
test("04 — Register form via self-service registration", async ({ page }) => {
  // First, get the share link from the previously created form
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("networkidle");

  // Open the recently created form to get its share link
  const recentForm = page
    .getByRole("link", { name: /patient satisfaction/i })
    .first();
  if (await recentForm.isVisible()) {
    await recentForm.click();
    await page.waitForLoadState("networkidle");
  }

  // Get the share link
  const shareButton = page.getByRole("button", { name: /share/i }).first();
  await shareButton.click();
  await page.waitForTimeout(2_000);

  // Copy the link (the URL in the share dialog)
  const linkInput = page.getByRole("textbox").first();
  const formShareLink = await linkInput.inputValue();

  // Now navigate to the registration form
  // The registration form URL should be provided by IT — using the known form ID
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("networkidle");

  // Open the registration form
  const regForm = page
    .getByRole("link", { name: /register.*form.*analytics/i })
    .first();
  if (await regForm.isVisible()) {
    await regForm.click();
    await page.waitForLoadState("networkidle");
  }

  await capture(page, "04-register-form-blank.png");

  // Fill in Q1: Form share link
  const linkField = page.getByPlaceholder(/enter your answer/i).first();
  if (await linkField.isVisible()) {
    await linkField.fill(formShareLink || "https://forms.office.com/...");
  }

  // Fill in Q2: Form name
  const nameFields = page.getByPlaceholder(/enter your answer/i);
  if ((await nameFields.count()) > 1) {
    await nameFields.nth(1).fill("Patient Satisfaction Survey");
  }

  // Fill in Q3: PHI flag — select "Yes" to demonstrate the approval flow
  const yesOption = page.getByRole("radio", { name: /yes/i }).first();
  if (await yesOption.isVisible()) {
    await yesOption.click();
  }

  await capture(page, "04-register-form-filled.png");

  // Submit the registration form
  const submitButton = page.getByRole("button", { name: /submit/i });
  if (await submitButton.isVisible()) {
    await submitButton.click();
    await page.waitForTimeout(3_000);
  }

  await capture(page, "04-register-form-confirmation.png");
});
