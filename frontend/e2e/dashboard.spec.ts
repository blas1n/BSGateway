import { test, expect } from "@playwright/test";

const TENANT = "test-tenant";
const mockAuth = async (page) => {
  const h = btoa(JSON.stringify({alg:"ES256",typ:"JWT"})).replace(/=/g,"");
  const p = btoa(JSON.stringify({sub:"t",email:"t@t.com",role:"authenticated",exp:Math.floor(Date.now()/1000)+3600,tenantId:TENANT,app_metadata:{role:"admin"}})).replace(/=/g,"");
  await page.evaluate(({h,p,TENANT}) => {
    sessionStorage.setItem("bsvibe_user", JSON.stringify({accessToken:h+"."+p+".s",refreshToken:"r",tenantId:TENANT,email:"t@t.com",role:"admin"}));
  }, {h,p,TENANT});
};

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/**", route => route.fulfill({status:200,contentType:"application/json",body:"{}"}));
    await page.goto("/");
    await mockAuth(page);
    await page.reload();
  });

  test("renders page after auth", async ({ page }) => {
    await page.waitForTimeout(2000);
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });
});
