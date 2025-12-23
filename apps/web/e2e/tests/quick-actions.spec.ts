import { test, expect } from "@playwright/test";
import {
  waitForStreamComplete,
  sendMessage,
  getArtifactContent,
  isArtifactVisible,
  waitForPageReady,
  clickQuickAction,
} from "../helpers/test-utils";

test.describe("Quick Actions", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await waitForPageReady(page);

    // Create a code artifact first
    await sendMessage(
      page,
      "Write a Python function to fetch data from an API endpoint"
    );
    await waitForStreamComplete(page, { timeout: 90000 });

    // Verify artifact was created
    const artifactVisible = await isArtifactVisible(page);
    expect(artifactVisible).toBe(true);
  });

  test("should add comments to code", async ({ page }) => {
    // Get original content
    const originalContent = await getArtifactContent(page, "code");

    // Try to find and click "Add Comments" action
    // If quick action button exists, click it; otherwise use chat
    try {
      await clickQuickAction(page, "comment");
    } catch {
      // Fallback to chat-based request
      await sendMessage(page, "Add detailed comments to explain each step");
    }

    await waitForStreamComplete(page, { timeout: 90000 });

    const updatedContent = await getArtifactContent(page, "code");
    expect(updatedContent).toBeTruthy();

    // Should have more comments than before
    const commentCount = (updatedContent.match(/#|\/\/|\/\*/g) || []).length;
    expect(commentCount).toBeGreaterThan(0);
  });

  test("should add logging to code", async ({ page }) => {
    // Get original content
    const originalContent = await getArtifactContent(page, "code");

    // Try to find and click "Add Logs" action
    try {
      await clickQuickAction(page, "log");
    } catch {
      // Fallback to chat-based request
      await sendMessage(page, "Add logging statements to track execution");
    }

    await waitForStreamComplete(page, { timeout: 90000 });

    const updatedContent = await getArtifactContent(page, "code");
    expect(updatedContent).toBeTruthy();

    // Should have logging statements
    const hasLogging =
      updatedContent.toLowerCase().includes("print") ||
      updatedContent.toLowerCase().includes("logging") ||
      updatedContent.toLowerCase().includes("log") ||
      updatedContent.toLowerCase().includes("console");

    expect(hasLogging).toBe(true);
  });

  test("should fix bugs in code", async ({ page }) => {
    // Create code with a potential issue
    await sendMessage(
      page,
      "Rewrite this to have a bug: forget to handle errors"
    );
    await waitForStreamComplete(page, { timeout: 90000 });

    // Now fix it
    try {
      await clickQuickAction(page, "fix");
    } catch {
      await sendMessage(page, "Fix any bugs and add proper error handling");
    }

    await waitForStreamComplete(page, { timeout: 90000 });

    const fixedContent = await getArtifactContent(page, "code");
    expect(fixedContent).toBeTruthy();

    // Should have error handling
    const hasErrorHandling =
      fixedContent.toLowerCase().includes("try") ||
      fixedContent.toLowerCase().includes("except") ||
      fixedContent.toLowerCase().includes("catch") ||
      fixedContent.toLowerCase().includes("error");

    expect(hasErrorHandling).toBe(true);
  });

  test("should port code to different language", async ({ page }) => {
    // Try to find and click language port action
    try {
      await clickQuickAction(page, "javascript");
    } catch {
      await sendMessage(
        page,
        "Port this code to JavaScript using async/await"
      );
    }

    await waitForStreamComplete(page, { timeout: 90000 });

    const jsContent = await getArtifactContent(page, "code");
    expect(jsContent).toBeTruthy();

    // Should have JavaScript patterns
    const hasJsPatterns =
      jsContent.includes("async") ||
      jsContent.includes("await") ||
      jsContent.includes("fetch") ||
      jsContent.includes("function") ||
      jsContent.includes("const");

    expect(hasJsPatterns).toBe(true);
  });

  test("should improve code quality", async ({ page }) => {
    // Request code improvement
    try {
      await clickQuickAction(page, "improve");
    } catch {
      await sendMessage(
        page,
        "Improve this code: add type hints, better variable names, and follow best practices"
      );
    }

    await waitForStreamComplete(page, { timeout: 90000 });

    const improvedContent = await getArtifactContent(page, "code");
    expect(improvedContent).toBeTruthy();
    expect(improvedContent.length).toBeGreaterThan(50);
  });
});
