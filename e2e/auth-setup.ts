/**
 * Auth setup script for the E2E screenshot pipeline.
 *
 * Opens Microsoft Edge to the M365 login page so the user can authenticate
 * manually. After login completes, saves the browser storage state to
 * .auth/state.json for reuse by Playwright capture scripts.
 *
 * Usage: npm run auth-setup
 */

import { chromium } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const TENANT_ID = "6dd0fc78-2408-43d6-a255-4383fbda3f76";
const LOGIN_URL = `https://login.microsoftonline.com/${TENANT_ID}`;
const FORMS_URL = "https://forms.office.com";
const AUTH_DIR = path.resolve(__dirname, ".auth");
const STATE_PATH = path.join(AUTH_DIR, "state.json");

async function main(): Promise<void> {
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  console.log("Launching Microsoft Edge for M365 authentication...");
  console.log(`Tenant: ${TENANT_ID}`);
  console.log();
  console.log("Please sign in when the browser opens.");
  console.log("The browser will close automatically after authentication.\n");

  const browser = await chromium.launch({
    channel: "msedge",
    headless: false,
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(LOGIN_URL);

  // Wait for the user to complete login and land on an authenticated page.
  // We consider auth complete when we reach the Forms home page or any
  // Office 365 page after login.
  console.log("Waiting for authentication to complete...");
  console.log("(Navigate to forms.office.com after signing in)\n");

  await page.goto(FORMS_URL);

  // Wait until the page shows authenticated content (Forms landing page)
  await page.waitForURL(/forms\.(office|microsoft)\.com/, {
    timeout: 300_000,
  });

  // Give the page a moment to fully load cookies and tokens
  await page.waitForTimeout(3_000);

  // Save the authenticated storage state
  await context.storageState({ path: STATE_PATH });

  console.log(`✓ Auth state saved to ${STATE_PATH}`);
  console.log("You can now run: npm run capture\n");

  await browser.close();
}

main().catch((error) => {
  console.error("Authentication setup failed:", error.message);
  process.exit(1);
});
