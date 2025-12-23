import { test, expect } from "@playwright/test";
import {
  waitForStreamComplete,
  sendMessage,
  getArtifactContent,
  isArtifactVisible,
  waitForPageReady,
  getArtifactVersionCount,
} from "../helpers/test-utils";

test.describe("Artifact Editing", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await waitForPageReady(page);

    // First, create an artifact to edit
    await sendMessage(
      page,
      "Write a simple Python function that adds two numbers"
    );
    await waitForStreamComplete(page, { timeout: 90000 });

    // Verify artifact was created
    const artifactVisible = await isArtifactVisible(page);
    expect(artifactVisible).toBe(true);
  });

  test("should rewrite entire artifact when requested", async ({ page }) => {
    // Get original content
    const originalContent = await getArtifactContent(page, "code");
    expect(originalContent).toBeTruthy();

    // Request a rewrite
    await sendMessage(page, "Convert this function to TypeScript with types");
    await waitForStreamComplete(page, { timeout: 90000 });

    // Get new content
    const newContent = await getArtifactContent(page, "code");
    expect(newContent).toBeTruthy();

    // Content should be different (converted to TypeScript)
    // Look for TypeScript type annotations
    const hasTypeAnnotations =
      newContent.includes(": number") ||
      newContent.includes(": string") ||
      newContent.includes("number)") ||
      newContent.includes("function");

    expect(hasTypeAnnotations).toBe(true);
  });

  test("should update artifact with additional functionality", async ({
    page,
  }) => {
    // Get original content
    const originalContent = await getArtifactContent(page, "code");

    // Request modification
    await sendMessage(
      page,
      "Add input validation to check if both arguments are numbers"
    );
    await waitForStreamComplete(page, { timeout: 90000 });

    // Get updated content
    const updatedContent = await getArtifactContent(page, "code");
    expect(updatedContent).toBeTruthy();

    // Should have validation logic
    const hasValidation =
      updatedContent.toLowerCase().includes("if") ||
      updatedContent.toLowerCase().includes("type") ||
      updatedContent.toLowerCase().includes("isinstance") ||
      updatedContent.toLowerCase().includes("number");

    expect(hasValidation).toBe(true);
  });

  test("should add documentation to existing code", async ({ page }) => {
    // Request adding documentation
    await sendMessage(
      page,
      "Add a detailed docstring explaining the function parameters and return value"
    );
    await waitForStreamComplete(page, { timeout: 90000 });

    // Get updated content
    const updatedContent = await getArtifactContent(page, "code");
    expect(updatedContent).toBeTruthy();

    // Should have documentation
    const hasDocumentation =
      updatedContent.includes('"""') ||
      updatedContent.includes("'''") ||
      updatedContent.includes("/**") ||
      updatedContent.includes("//") ||
      updatedContent.includes("#");

    expect(hasDocumentation).toBe(true);
  });

  test("should maintain artifact after multiple edits", async ({ page }) => {
    // First edit
    await sendMessage(page, "Add error handling for invalid inputs");
    await waitForStreamComplete(page, { timeout: 90000 });

    let content = await getArtifactContent(page, "code");
    expect(content).toBeTruthy();

    // Second edit
    await sendMessage(page, "Add a return type annotation");
    await waitForStreamComplete(page, { timeout: 90000 });

    content = await getArtifactContent(page, "code");
    expect(content).toBeTruthy();

    // Third edit
    await sendMessage(page, "Add logging statements");
    await waitForStreamComplete(page, { timeout: 90000 });

    content = await getArtifactContent(page, "code");
    expect(content).toBeTruthy();

    // Content should still be valid code
    expect(content.length).toBeGreaterThan(50);
  });

  test("should convert code to different language", async ({ page }) => {
    // Request language conversion
    await sendMessage(page, "Convert this to JavaScript");
    await waitForStreamComplete(page, { timeout: 90000 });

    const jsContent = await getArtifactContent(page, "code");
    expect(jsContent).toBeTruthy();

    // Should have JavaScript patterns
    const hasJsPatterns =
      jsContent.includes("function") ||
      jsContent.includes("const") ||
      jsContent.includes("let") ||
      jsContent.includes("=>");

    expect(hasJsPatterns).toBe(true);
  });
});
