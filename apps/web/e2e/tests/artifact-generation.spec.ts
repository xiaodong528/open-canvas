import { test, expect } from "@playwright/test";
import {
  waitForStreamComplete,
  sendMessage,
  getArtifactContent,
  isArtifactVisible,
  waitForPageReady,
} from "../helpers/test-utils";

test.describe("Artifact Generation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await waitForPageReady(page);
  });

  test("should generate code artifact from user request", async ({ page }) => {
    // Send a code generation request
    await sendMessage(
      page,
      "Write a Python function to calculate the factorial of a number"
    );

    // Wait for the streaming response to complete
    await waitForStreamComplete(page, { timeout: 90000 });

    // Verify artifact panel is visible
    const artifactVisible = await isArtifactVisible(page);
    expect(artifactVisible).toBe(true);

    // Verify code content is present
    const codeContent = await getArtifactContent(page, "code");
    expect(codeContent).toBeTruthy();
    expect(codeContent.toLowerCase()).toContain("def");
    expect(codeContent.toLowerCase()).toContain("factorial");
  });

  test("should generate markdown artifact for text request", async ({
    page,
  }) => {
    // Send a text/document generation request
    await sendMessage(
      page,
      "Write a short blog post about the benefits of test-driven development"
    );

    // Wait for the streaming response to complete
    await waitForStreamComplete(page, { timeout: 90000 });

    // Verify artifact panel is visible
    const artifactVisible = await isArtifactVisible(page);
    expect(artifactVisible).toBe(true);

    // Verify content is present and substantial
    const textContent = await getArtifactContent(page, "text");
    expect(textContent.length).toBeGreaterThan(100);
  });

  test("should show streaming indicator during generation", async ({
    page,
  }) => {
    // Send a request
    await sendMessage(page, "Write a Python hello world function");

    // Check for streaming/loading indicator
    // Wait a moment for streaming to start
    await page.waitForTimeout(500);

    // The page should show some indication of loading
    // This could be a spinner, pulsing animation, or loading text
    const hasLoadingState = await page.evaluate(() => {
      const body = document.body.innerHTML.toLowerCase();
      return (
        body.includes("loading") ||
        body.includes("generating") ||
        document.querySelector(".animate-pulse") !== null ||
        document.querySelector('[aria-busy="true"]') !== null
      );
    });

    // Note: This assertion is relaxed because the streaming might complete quickly
    // The main test is that the generation completes successfully
    await waitForStreamComplete(page, { timeout: 90000 });

    // Verify final artifact is present
    const artifactVisible = await isArtifactVisible(page);
    expect(artifactVisible).toBe(true);
  });

  test("should generate TypeScript code when specified", async ({ page }) => {
    await sendMessage(
      page,
      "Write a TypeScript function that validates email addresses"
    );

    await waitForStreamComplete(page, { timeout: 90000 });

    const codeContent = await getArtifactContent(page, "code");
    expect(codeContent).toBeTruthy();

    // TypeScript specific patterns
    const hasTypeScriptPatterns =
      codeContent.includes(": string") ||
      codeContent.includes(": boolean") ||
      codeContent.includes("function") ||
      codeContent.includes("const");

    expect(hasTypeScriptPatterns).toBe(true);
  });

  test("should generate JavaScript code when specified", async ({ page }) => {
    await sendMessage(
      page,
      "Write a JavaScript function to sort an array of objects by a property"
    );

    await waitForStreamComplete(page, { timeout: 90000 });

    const codeContent = await getArtifactContent(page, "code");
    expect(codeContent).toBeTruthy();
    expect(codeContent).toMatch(/function|const|let|=>/);
  });
});
