import { test, expect } from "@playwright/test";

test.describe("VigilaGraph IA — Smoke Tests", () => {
  test("landing page redirects to login", async ({ page }) => {
    await page.goto("/");
    await page.waitForURL("**/login");
    await expect(page.getByRole("heading", { name: /iniciar sesi/i })).toBeVisible();
  });

  test("login page renders correctly", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /iniciar sesi/i })).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole("button", { name: /ingresar/i })).toBeVisible();
  });

  test("register page renders correctly", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: /crear cuenta/i })).toBeVisible();
    await expect(page.locator('input[id="name"]')).toBeVisible();
    await expect(page.locator('input[id="email"]')).toBeVisible();
    await expect(page.locator('input[id="password"]')).toBeVisible();
  });

  test("shows validation errors on empty login", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /ingresar/i }).click();
    await expect(page.getByText(/ingres[áa] un correo v[áa]lido/i)).toBeVisible();
  });

  test("dashboard redirects to login when unauthenticated", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForURL("**/login");
    await expect(page.getByRole("heading", { name: /iniciar sesi/i })).toBeVisible();
  });
});
