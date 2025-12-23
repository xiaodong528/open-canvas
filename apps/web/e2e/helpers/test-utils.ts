import { Page, Locator, expect } from "@playwright/test";

/**
 * Wait options for stream completion
 */
export interface WaitOptions {
  timeout?: number;
  pollInterval?: number;
}

/**
 * Wait for the streaming response to complete
 * Detects when the UI is no longer showing loading state
 */
export async function waitForStreamComplete(
  page: Page,
  options: WaitOptions = {}
): Promise<void> {
  const { timeout = 90000 } = options;

  // Wait for any loading indicators to disappear
  // The app uses various loading states - we check for common patterns
  const loadingSelectors = [
    '[data-loading="true"]',
    ".animate-pulse",
    '[aria-busy="true"]',
  ];

  // First, wait a moment for streaming to potentially start
  await page.waitForTimeout(1000);

  // Then wait for all loading indicators to disappear
  for (const selector of loadingSelectors) {
    const loadingElement = page.locator(selector).first();
    const isVisible = await loadingElement.isVisible().catch(() => false);
    if (isVisible) {
      await expect(loadingElement).not.toBeVisible({ timeout });
    }
  }

  // Additional stabilization wait
  await page.waitForTimeout(500);
}

/**
 * Send a message in the chat input and wait for response
 */
export async function sendMessage(page: Page, message: string): Promise<void> {
  // Find the chat input - try multiple selectors
  const inputSelectors = [
    'textarea[placeholder*="message"]',
    'textarea[placeholder*="Message"]',
    'input[placeholder*="message"]',
    "textarea",
    '[role="textbox"]',
  ];

  let input: Locator | null = null;
  for (const selector of inputSelectors) {
    const candidate = page.locator(selector).first();
    if (await candidate.isVisible().catch(() => false)) {
      input = candidate;
      break;
    }
  }

  if (!input) {
    throw new Error("Could not find chat input");
  }

  // Type the message
  await input.fill(message);

  // Submit - try Enter key first, then look for submit button
  await page.keyboard.press("Enter");
}

/**
 * Get the content of the artifact panel
 */
export async function getArtifactContent(
  page: Page,
  type: "code" | "text" = "code"
): Promise<string> {
  // The artifact panel contains either CodeMirror (code) or BlockNote (text)
  if (type === "code") {
    // CodeMirror content
    const codeSelectors = [
      ".cm-content",
      '[role="code"]',
      "pre code",
      ".CodeMirror",
    ];

    for (const selector of codeSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible().catch(() => false)) {
        return (await element.textContent()) || "";
      }
    }
  } else {
    // BlockNote/Markdown content
    const textSelectors = [
      ".bn-editor",
      '[role="textbox"]',
      ".ProseMirror",
      '[contenteditable="true"]',
    ];

    for (const selector of textSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible().catch(() => false)) {
        return (await element.textContent()) || "";
      }
    }
  }

  return "";
}

/**
 * Check if an artifact panel is visible
 */
export async function isArtifactVisible(page: Page): Promise<boolean> {
  // The artifact panel should be in the right side of the layout
  const artifactSelectors = [
    '[class*="artifact"]',
    '[class*="Artifact"]',
    ".cm-editor",
    ".bn-editor",
  ];

  for (const selector of artifactSelectors) {
    const element = page.locator(selector).first();
    if (await element.isVisible().catch(() => false)) {
      return true;
    }
  }

  return false;
}

/**
 * Get the last assistant message from the chat
 */
export async function getLastAssistantMessage(page: Page): Promise<string> {
  // Find assistant messages - they typically have specific styling or role
  const messageSelectors = [
    '[data-role="assistant"]',
    '[class*="assistant"]',
    ".message-assistant",
  ];

  for (const selector of messageSelectors) {
    const messages = page.locator(selector);
    const count = await messages.count();
    if (count > 0) {
      const lastMessage = messages.last();
      return (await lastMessage.textContent()) || "";
    }
  }

  return "";
}

/**
 * Wait for the page to be ready for interaction
 */
export async function waitForPageReady(page: Page): Promise<void> {
  // Wait for network to be idle
  await page.waitForLoadState("networkidle", { timeout: 30000 });

  // Wait for main content to be visible
  await page.waitForTimeout(1000);
}

/**
 * Select text in a code editor
 * Note: This is a simplified version - actual implementation may need
 * to interact with CodeMirror's API
 */
export async function selectCodeRange(
  page: Page,
  startLine: number,
  startCol: number,
  endLine: number,
  endCol: number
): Promise<void> {
  // This would need to be implemented based on the specific editor
  // For now, we'll use a simplified approach
  const editor = page.locator(".cm-editor").first();
  await editor.click();

  // Use keyboard shortcuts to select
  // Ctrl+A to select all as a fallback
  await page.keyboard.press("Control+a");
}

/**
 * Click a quick action button
 */
export async function clickQuickAction(
  page: Page,
  actionName: string
): Promise<void> {
  // Quick actions are typically buttons with specific text or icons
  const actionButton = page.getByRole("button", {
    name: new RegExp(actionName, "i"),
  });

  if (await actionButton.isVisible()) {
    await actionButton.click();
    return;
  }

  // Try finding by text content
  const buttonByText = page.locator(`button:has-text("${actionName}")`).first();
  if (await buttonByText.isVisible()) {
    await buttonByText.click();
    return;
  }

  throw new Error(`Quick action "${actionName}" not found`);
}

/**
 * Get the artifact version/history count
 */
export async function getArtifactVersionCount(page: Page): Promise<number> {
  // Look for version indicators in the UI
  const versionIndicators = [
    '[class*="version"]',
    '[class*="history"]',
    '[aria-label*="version"]',
  ];

  for (const selector of versionIndicators) {
    const element = page.locator(selector).first();
    if (await element.isVisible().catch(() => false)) {
      const text = await element.textContent();
      const match = text?.match(/\d+/);
      if (match) {
        return parseInt(match[0], 10);
      }
    }
  }

  return 1; // Default to 1 if no version indicator found
}

/**
 * Check if a specific language is displayed for the artifact
 */
export async function getArtifactLanguage(page: Page): Promise<string | null> {
  // Language indicators are typically shown in the artifact header
  const languageSelectors = [
    '[class*="language"]',
    '[data-language]',
    'select[name*="language"]',
  ];

  for (const selector of languageSelectors) {
    const element = page.locator(selector).first();
    if (await element.isVisible().catch(() => false)) {
      // Try data attribute first
      const dataLang = await element.getAttribute("data-language");
      if (dataLang) return dataLang;

      // Then try text content
      const text = await element.textContent();
      if (text) return text.toLowerCase().trim();
    }
  }

  return null;
}
