/**
 * Custom Playwright fixture that uses a persistent browser profile
 * for M365 authentication. All capture scripts import `test` and `expect`
 * from this file instead of from @playwright/test directly.
 */

import { test as base, expect, chromium, type Page } from "@playwright/test";
import * as path from "path";

const PROFILE_DIR = path.resolve(__dirname, ".auth/profile");

type CaptureFixtures = {
  authedPage: Page;
};

export const test = base.extend<CaptureFixtures>({
  authedPage: async ({}, use) => {
    const context = await chromium.launchPersistentContext(PROFILE_DIR, {
      channel: "msedge",
      headless: true,
      viewport: { width: 1440, height: 900 },
    });

    const page = context.pages()[0] || (await context.newPage());
    await use(page);
    await context.close();
  },
});

export { expect };
