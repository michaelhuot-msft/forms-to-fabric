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
  await page.waitForLoadState("networkidle");

  // Open the registration form — opens in a new tab
  const [formPage] = await Promise.all([
    page.context().waitForEvent("page"),
    page
      .getByRole("button", { name: /Register Your Form for Analytics/i })
      .first()
      .click(),
  ]);

  await formPage.waitForLoadState("networkidle");
  await formPage.waitForTimeout(2_000);

  // Click Preview to see the responder view
  await formPage.getByRole("button", { name: /Preview/i }).click();
  await formPage.waitForTimeout(3_000);

  await capture(formPage, "04-register-form-blank.png");

  // Fill in text fields if visible
  const textInputs = formPage.getByRole("textbox");
  const textCount = await textInputs.count();
  if (textCount > 0) {
    await textInputs.first().fill("https://forms.office.com/Pages/ResponsePage.aspx?id=example");
  }
  if (textCount > 1) {
    await textInputs.nth(1).fill("Patient Satisfaction Survey");
  }

  await capture(formPage, "04-register-form-filled.png");
  await capture(formPage, "04-register-form-confirmation.png");
});
