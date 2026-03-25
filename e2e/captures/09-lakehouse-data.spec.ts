import { test } from "../fixtures";
import { capture, URLS } from "../helpers";

test("09 — Fabric Lakehouse raw and curated tables", async ({ authedPage: page }) => {
  await page.goto(URLS.fabric);
  await page.waitForLoadState("load");
  await page.waitForTimeout(10_000);

  // If "Pick an account" page appears, select the first account
  const pickAccount = page.getByRole("heading", { name: /Pick an account/i });
  if (await pickAccount.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await page.getByRole("listitem").first().click();
    await page.waitForLoadState("load");
    await page.waitForTimeout(10_000);
  }

  // Navigate to Workspaces in the left nav
  const workspaces = page.getByRole("menuitem", { name: "Workspaces" });
  if (await workspaces.isVisible()) {
    await workspaces.click();
    await page.waitForTimeout(3_000);
  }

  // Click the Forms to Fabric Analytics workspace
  const workspace = page.getByRole("button", {
    name: /Forms to Fabric Analytics/i,
  });
  if (await workspace.isVisible()) {
    await workspace.click();
    await page.waitForLoadState("load");
    await page.waitForTimeout(5_000);
  }

  await capture(page, "09-lakehouse-overview.png");

  // Open the Lakehouse
  const lakehouse = page.getByRole("link", { name: "forms_lakehouse" });
  if (await lakehouse.isVisible()) {
    await lakehouse.click();
    await page.waitForLoadState("load");
    await page.waitForTimeout(10_000);
  }

  await capture(page, "09-lakehouse-raw-table.png");

  // Expand the Tables tree item if visible
  const tablesTree = page.getByRole("treeitem", { name: /Tables/i }).first();
  if (await tablesTree.isVisible()) {
    await tablesTree.click();
    await page.waitForTimeout(3_000);
  }

  await capture(page, "09-lakehouse-curated-table.png");
});
