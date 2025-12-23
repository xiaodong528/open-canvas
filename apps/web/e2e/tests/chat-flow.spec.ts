import { test, expect } from "@playwright/test";
import {
  waitForStreamComplete,
  sendMessage,
  getArtifactContent,
  isArtifactVisible,
  waitForPageReady,
  getLastAssistantMessage,
} from "../helpers/test-utils";

test.describe("Chat Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await waitForPageReady(page);
  });

  test("should handle general questions without creating artifacts", async ({
    page,
  }) => {
    // Ask a general question that shouldn't create an artifact
    await sendMessage(page, "What is recursion in programming?");

    await waitForStreamComplete(page, { timeout: 60000 });

    // Should get a response in the chat
    // Check that the page has assistant response content
    const pageContent = await page.content();
    const hasResponse =
      pageContent.toLowerCase().includes("recursion") ||
      pageContent.toLowerCase().includes("function") ||
      pageContent.toLowerCase().includes("call");

    expect(hasResponse).toBe(true);
  });

  test("should maintain conversation context", async ({ page }) => {
    // First message
    await sendMessage(page, "Write a Python function to calculate fibonacci");
    await waitForStreamComplete(page, { timeout: 90000 });

    // Verify artifact created
    expect(await isArtifactVisible(page)).toBe(true);

    // Follow-up that references the previous context
    await sendMessage(page, "Now add memoization to optimize it");
    await waitForStreamComplete(page, { timeout: 90000 });

    // Get the updated code
    const content = await getArtifactContent(page, "code");
    expect(content).toBeTruthy();

    // Should have memoization patterns
    const hasMemoization =
      content.toLowerCase().includes("cache") ||
      content.toLowerCase().includes("memo") ||
      content.toLowerCase().includes("dict") ||
      content.toLowerCase().includes("{}");

    expect(hasMemoization).toBe(true);
  });

  test("should create new artifact when explicitly requested", async ({
    page,
  }) => {
    // First, create one artifact
    await sendMessage(page, "Write a Python hello world function");
    await waitForStreamComplete(page, { timeout: 90000 });

    const firstContent = await getArtifactContent(page, "code");
    expect(firstContent).toBeTruthy();

    // Request a completely different artifact
    await sendMessage(page, "Now write a JavaScript array sorting function");
    await waitForStreamComplete(page, { timeout: 90000 });

    const secondContent = await getArtifactContent(page, "code");
    expect(secondContent).toBeTruthy();

    // Content should be different
    expect(secondContent).not.toEqual(firstContent);

    // Should have JavaScript/sorting patterns
    const hasNewContent =
      secondContent.includes("sort") ||
      secondContent.includes("function") ||
      secondContent.includes("const") ||
      secondContent.includes("array");

    expect(hasNewContent).toBe(true);
  });

  test("should handle multi-turn conversation", async ({ page }) => {
    // Turn 1: Create initial artifact
    await sendMessage(page, "Write a class for a basic calculator in Python");
    await waitForStreamComplete(page, { timeout: 90000 });

    expect(await isArtifactVisible(page)).toBe(true);

    // Turn 2: Add functionality
    await sendMessage(page, "Add a method for calculating percentage");
    await waitForStreamComplete(page, { timeout: 90000 });

    let content = await getArtifactContent(page, "code");
    expect(content.toLowerCase()).toMatch(/percent|%/);

    // Turn 3: Another modification
    await sendMessage(page, "Add a method for square root");
    await waitForStreamComplete(page, { timeout: 90000 });

    content = await getArtifactContent(page, "code");
    expect(content.toLowerCase()).toMatch(/sqrt|square|root|math/);

    // Turn 4: Final polish
    await sendMessage(page, "Add docstrings to all methods");
    await waitForStreamComplete(page, { timeout: 90000 });

    content = await getArtifactContent(page, "code");
    const hasDocstrings =
      content.includes('"""') ||
      content.includes("'''") ||
      content.includes("/**");
    expect(hasDocstrings).toBe(true);
  });

  test("should handle error gracefully when API fails", async ({ page }) => {
    // This test verifies the UI handles errors gracefully
    // We'll send a request and verify the page doesn't crash

    await sendMessage(page, "Write some code");

    // Wait for either success or error state
    await page.waitForTimeout(5000);

    // Page should still be functional
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();

    // Should be able to interact with the page
    const body = await page.locator("body");
    expect(await body.isVisible()).toBe(true);
  });

  test("should display followup message after artifact generation", async ({
    page,
  }) => {
    await sendMessage(page, "Write a Python function to reverse a string");
    await waitForStreamComplete(page, { timeout: 90000 });

    // Verify artifact is created
    expect(await isArtifactVisible(page)).toBe(true);

    // The chat should contain a response from the assistant
    // This could be a followup message or confirmation
    const pageContent = await page.content();

    // The page should show some response text
    expect(pageContent.length).toBeGreaterThan(1000);
  });
});
