import { defineConfig } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const authStatePath = path.resolve(__dirname, ".auth/state.json");

function validateAuthState(): string {
  if (!fs.existsSync(authStatePath)) {
    throw new Error(
      `Auth state not found at ${authStatePath}.\n` +
        `Run "npm run auth-setup" to authenticate with M365 first.`
    );
  }
  return authStatePath;
}

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
    storageState: validateAuthState(),
    viewport: { width: 1440, height: 900 },
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
    screenshot: "off",
  },
  projects: [
    {
      name: "capture",
      testDir: "./captures",
    },
  ],
});

export { screenshotDir };
