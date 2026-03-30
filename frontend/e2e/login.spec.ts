import { test, expect } from "@playwright/test";

test.describe("Login Page", () => {
  test("renders login form", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Sign in with BSVibe")).toBeVisible();
  });

  test("redirects to auth.bsvibe.dev on click", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Sign in with BSVibe").click();
    await page.waitForURL(/auth\.bsvibe\.dev/);
    expect(page.url()).toContain("auth.bsvibe.dev");
  });
});
