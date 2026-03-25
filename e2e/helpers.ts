/**
 * Shared helpers for E2E screenshot capture scripts.
 */

import * as path from "path";
import * as fs from "fs";
import type { Page } from "@playwright/test";

export const SCREENSHOT_DIR = path.resolve(__dirname, "../docs/images/e2e");

/**
 * Capture a full-page screenshot with a descriptive filename.
 * Filenames follow the pattern NN-descriptive-name.png.
 */
export async function capture(
  page: Page,
  filename: string
): Promise<string> {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  const filePath = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: filePath, fullPage: true });
  console.log(`  📸 ${filename}`);
  return filePath;
}

/** M365 URLs used across capture scripts. */
export const URLS = {
  formsHome: "https://forms.office.com/Pages/DesignPageV2.aspx",
  powerAutomate: "https://make.powerautomate.com",
  fabric: "https://app.fabric.microsoft.com",
} as const;
