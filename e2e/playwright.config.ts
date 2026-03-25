import { defineConfig } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const profileDir = path.resolve(__dirname, ".auth/profile");

function validateProfile(): void {
  if (!fs.existsSync(profileDir)) {
    throw new Error(
      `Auth profile not found at ${profileDir}.\n` +
        `Run "npm run auth-setup" to authenticate with M365 first.`
    );
  }
}

validateProfile();

const screenshotDir = path.resolve(__dirname, "../docs/images/e2e");

export default defineConfig({
  testDir: "./captures",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 30_000 },
  use: {
    channel: "msedge",
    viewport: { width: 1440, height: 900 },
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
    screenshot: "off",
    launchOptions: {
      channel: "msedge",
    },
  },
  projects: [
    {
      name: "capture",
      testDir: "./captures",
    },
  ],
});

export { screenshotDir, profileDir };
