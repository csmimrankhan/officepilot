import { test, expect } from "@playwright/experimental-ct-react";

test.describe("App health", () => {

  test("backend health endpoint returns 200", async ({ request }) => {
    const resp = await request.get("http://localhost:8000/api/health");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.ok).toBe(true);
    expect(body.app).toBe("officepilot-ai");
    expect(body.state).toBe("online");
  });

  test("frontend loads the landing page", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

});
