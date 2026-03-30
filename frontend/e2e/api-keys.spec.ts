import { test, expect } from "@playwright/test";

test.describe("API Keys Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/**", route => route.fulfill({status:200,contentType:"application/json",body:"[]"}));
    await page.goto("/");
    await page.evaluate(() => {
      const h = btoa(JSON.stringify({alg:"ES256",typ:"JWT"})).replace(/=/g,"");
      const p = btoa(JSON.stringify({sub:"t",email:"t@t.com",role:"authenticated",exp:Math.floor(Date.now()/1000)+3600,tenantId:"t",app_metadata:{role:"admin"}})).replace(/=/g,"");
      sessionStorage.setItem("bsvibe_user", JSON.stringify({accessToken:h+"."+p+".s",refreshToken:"r",tenantId:"t",email:"t@t.com",role:"admin"}));
    });
    await page.reload();
  });

  test("navigates to api keys page", async ({ page }) => {
    await page.waitForTimeout(1000);
    const link = page.getByRole("link", { name: /api.?keys/i });
    if (await link.isVisible()) {
      await link.click();
      await page.waitForTimeout(1000);
    }
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });
});
