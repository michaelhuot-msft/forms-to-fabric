/**
 * Auth setup script for the E2E screenshot pipeline.
 *
 * Opens Microsoft Edge with a persistent browser profile so the user can
 * authenticate manually. The profile directory stores all auth state (cookies,
 * localStorage, IndexedDB, MSAL tokens) and is reused by capture scripts.
 *
 * Usage: npm run auth-setup
 */

import { chromium } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const TENANT_ID = "6dd0fc78-2408-43d6-a255-4383fbda3f76";
const PROFILE_DIR = path.resolve(__dirname, ".auth/profile");
const FORMS_APP = "https://forms.office.com/Pages/DesignPageV2.aspx";

async function main(): Promise<void> {
  if (!fs.existsSync(PROFILE_DIR)) {
    fs.mkdirSync(PROFILE_DIR, { recursive: true });
  }

  console.log("Launching Microsoft Edge with persistent profile...");
  console.log(`Tenant: ${TENANT_ID}`);
  console.log(`Profile: ${PROFILE_DIR}`);
  console.log();
  console.log("Please sign in when the browser opens.");
  console.log("Once you see the Forms home page with your forms, close the browser.\n");

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    channel: "msedge",
    headless: false,
    viewport: { width: 1440, height: 900 },
  });

  const page = context.pages()[0] || (await context.newPage());

  await page.goto(FORMS_APP);

  console.log("Waiting for authentication to complete...");
  console.log("(Close the browser window when you see the Forms home page)\n");

  // Wait until the browser is closed by the user
  await new Promise<void>((resolve) => {
    context.on("close", () => resolve());
  });

  console.log("✓ Auth profile saved to " + PROFILE_DIR);
  console.log("You can now run: npm run capture\n");
}

main().catch((error) => {
  console.error("Authentication setup failed:", error.message);
  process.exit(1);
});
