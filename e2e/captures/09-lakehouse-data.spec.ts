import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("09 — Fabric Lakehouse raw and curated tables", async ({ authedPage: page }) => {
  await page.goto(URLS.fabric);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(5_000);

  // Navigate to the Lakehouse
  // Look for the workspace or Lakehouse link in the Fabric portal
  const lakehouses = page.getByRole("link", { name: /lakehouse/i }).first();
  if (await lakehouses.isVisible()) {
    await lakehouses.click();
    await page.waitForLoadState("networkidle");
  }

  await page.waitForTimeout(3_000);

  await capture(page, "09-lakehouse-overview.png");

  // Navigate to the Tables section to show raw and curated data
  const tablesSection = page.getByRole("treeitem", { name: /tables/i }).first();
  if (await tablesSection.isVisible()) {
    await tablesSection.click();
    await page.waitForTimeout(2_000);
  }

  // Expand and show the raw table
  const rawTable = page
    .getByRole("treeitem", { name: /patient_satisfaction$/i })
    .first();
  if (await rawTable.isVisible()) {
    await rawTable.click();
    await page.waitForTimeout(3_000);
  }

  await capture(page, "09-lakehouse-raw-table.png");

  // Show the curated (de-identified) table
  const curatedTable = page
    .getByRole("treeitem", { name: /patient_satisfaction_curated/i })
    .first();
  if (await curatedTable.isVisible()) {
    await curatedTable.click();
    await page.waitForTimeout(3_000);
  }

  await capture(page, "09-lakehouse-curated-table.png");
});
