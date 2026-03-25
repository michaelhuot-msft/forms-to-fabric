import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("02 — Create a new form as a clinician", async ({ authedPage: page }) => {
  await page.goto(URLS.formsHome);
  await page.waitForLoadState("networkidle");

  // Click "Create a new form" — opens in a new tab
  const [newPage] = await Promise.all([
    page.context().waitForEvent("page"),
    page.getByRole("button", { name: "Create a new form" }).click(),
  ]);

  await newPage.waitForLoadState("networkidle");
  await newPage.waitForTimeout(3_000);

  // Click the form title heading to edit it
  const titleButton = newPage.getByRole("heading", {
    name: /Form title/i,
  });
  await titleButton.click();
  await newPage.waitForTimeout(500);

  // Clear and type new title
  await newPage.keyboard.press("Control+A");
  await newPage.keyboard.type("Patient Satisfaction Survey");
  // Dismiss title editing
  await newPage.keyboard.press("Escape");
  await newPage.waitForTimeout(2_000);

  await capture(newPage, "02-create-form-title.png");

  // After title edit, question type buttons collapse — expand via "Quick start with"
  const quickStart = newPage.getByRole("button", { name: "Quick start with" });
  if (await quickStart.isVisible()) {
    await quickStart.click();
    await newPage.waitForTimeout(1_000);
  }

  // Add a Choice question
  const choiceBtn = newPage.getByRole("button", { name: "Choice" }).first();
  await choiceBtn.waitFor({ state: "visible", timeout: 10_000 });
  await choiceBtn.click();
  await newPage.waitForTimeout(3_000);

  await capture(newPage, "02-create-form-question.png");
});
