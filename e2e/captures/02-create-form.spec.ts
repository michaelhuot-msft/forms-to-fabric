import { test } from "@playwright/test";
import { capture, URLS } from "../helpers";

test("02 — Create a new form as a clinician", async ({ page }) => {
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("networkidle");

  // Click "New Form" to start creating
  await page.getByRole("button", { name: /new form/i }).click();
  await page.waitForLoadState("networkidle");

  // Add a title
  await page.getByPlaceholder(/untitled form/i).click();
  await page.keyboard.type("Patient Satisfaction Survey");

  // Add a description
  await page.getByPlaceholder(/description/i).click();
  await page.keyboard.type(
    "Please help us improve by sharing your experience."
  );

  await capture(page, "02-create-form-title.png");

  // Add a Choice question
  await page.getByRole("button", { name: /add new/i }).click();
  await page.waitForTimeout(1_000);

  // Select "Choice" question type
  const choiceOption = page.getByRole("button", { name: /choice/i }).first();
  if (await choiceOption.isVisible()) {
    await choiceOption.click();
  }

  await page.waitForTimeout(1_000);

  // Type the question
  await page.getByPlaceholder(/question/i).first().click();
  await page.keyboard.type(
    "How would you rate your overall experience today?"
  );

  await capture(page, "02-create-form-question.png");
});
