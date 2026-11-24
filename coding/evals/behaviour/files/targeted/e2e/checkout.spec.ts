import { test, expect } from "@playwright/test";

test("checkout shows the cart total", async ({ page }) => {
  await page.goto("/cart");
  await expect(page.getByTestId("total")).toHaveText("$12.00");
});
