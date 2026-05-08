import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Trip planning happy path", () => {
  test("homepage is accessible", async ({ page }) => {
    await page.goto("/");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });

  test("keyboard-only user can fill the form", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab"); // skip link
    await page.keyboard.press("Tab"); // header link
    // Tab to destination
    while (!(await page.locator(":focus").evaluate((el) => (el as HTMLElement).id === "destination"))) {
      await page.keyboard.press("Tab");
    }
    await page.keyboard.type("Manali");
    await expect(page.locator("#destination")).toHaveValue("Manali");
  });
});
