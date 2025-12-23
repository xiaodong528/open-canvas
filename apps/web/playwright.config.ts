import { defineConfig, devices } from "@playwright/test";
import path from "path";

/**
 * Playwright configuration for Open Canvas E2E tests
 *
 * Test structure:
 * - Artifact generation tests
 * - Artifact editing tests
 * - Quick actions tests
 * - Chat flow tests
 */
export default defineConfig({
  testDir: "./e2e/tests",
  fullyParallel: false, // E2E tests run sequentially for stability
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["list"], // Console output
  ],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // Increase timeout for LLM responses
    actionTimeout: 60000,
  },

  // Global timeout for each test
  timeout: 120000,

  // Expect timeout for assertions
  expect: {
    timeout: 30000,
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],

  // Web servers to start before tests
  webServer: [
    {
      command: "cd ../agents-py && uv run langgraph dev --port 54367",
      url: "http://localhost:54367/ok",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "yarn dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],

  // Output directory for test artifacts
  outputDir: "test-results/",
});
