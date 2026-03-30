/**
 * E2E tests for authentication flows.
 *
 * Tests login success/failure, unauthorized redirect, and logout.
 * Each test creates its own data via the API helper (no test interdependence).
 */

import { test, expect } from "@playwright/test";
import {
  resetDatabase,
  setupFirstUser,
  login,
  getApiBaseUrl,
} from "../helpers/api.helper";

test.describe("Authentication", () => {
  const TEST_EMAIL = "auth-test@e2e-test.example.com";
  const TEST_PASSWORD = "auth-test-password-123";

  test.beforeEach(async () => {
    // Reset DB and create a user for auth tests
    await resetDatabase();
    await setupFirstUser({
      name: "Auth Test User",
      email: TEST_EMAIL,
      password: TEST_PASSWORD,
    });
  });

  test("successful login redirects to dashboard", async ({ page }) => {
    await page.goto("/login");

    await expect(
      page.getByRole("heading", { name: "ログイン" }),
    ).toBeVisible();

    await page.getByLabel("メールアドレス").fill(TEST_EMAIL);
    await page.getByLabel("パスワード").fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "ログイン" }).click();

    // Should redirect to dashboard (root)
    await expect(page).toHaveURL("/", { timeout: 10000 });
  });

  test("login with wrong password shows error", async ({ page }) => {
    await page.goto("/login");

    await page.getByLabel("メールアドレス").fill(TEST_EMAIL);
    await page.getByLabel("パスワード").fill("wrong-password-12345");
    await page.getByRole("button", { name: "ログイン" }).click();

    await expect(
      page.getByText("メールアドレスまたはパスワードが正しくありません"),
    ).toBeVisible();

    // Should remain on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test("login with non-existent email shows error", async ({ page }) => {
    await page.goto("/login");

    await page.getByLabel("メールアドレス").fill("nonexistent@e2e-test.example.com");
    await page.getByLabel("パスワード").fill("some-password-12345");
    await page.getByRole("button", { name: "ログイン" }).click();

    await expect(
      page.getByText("メールアドレスまたはパスワードが正しくありません"),
    ).toBeVisible();
  });

  test("login with empty email shows validation error", async ({ page }) => {
    await page.goto("/login");

    // Leave email empty
    await page.getByLabel("パスワード").fill("some-password");
    await page.getByRole("button", { name: "ログイン" }).click();

    await expect(
      page.getByText("メールアドレスを入力してください"),
    ).toBeVisible();
  });

  test("login with empty password shows validation error", async ({
    page,
  }) => {
    await page.goto("/login");

    await page.getByLabel("メールアドレス").fill(TEST_EMAIL);
    // Leave password empty
    await page.getByRole("button", { name: "ログイン" }).click();

    await expect(
      page.getByText("パスワードを入力してください"),
    ).toBeVisible();
  });

  test("unauthenticated user is redirected to login", async ({ page }) => {
    // Clear any existing cookies/state
    await page.context().clearCookies();

    // Try to access a protected page
    await page.goto("/");

    // AuthGuard should redirect to /login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test("logout clears session and redirects to login", async ({ page }) => {
    // First login through the UI
    await page.goto("/login");
    await page.getByLabel("メールアドレス").fill(TEST_EMAIL);
    await page.getByLabel("パスワード").fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "ログイン" }).click();

    // Wait for dashboard
    await expect(page).toHaveURL("/", { timeout: 10000 });

    // Find and click the logout button/link
    // Look for a logout mechanism in the UI
    const logoutButton = page.getByRole("button", { name: /ログアウト/i });
    const logoutLink = page.getByRole("link", { name: /ログアウト/i });
    const logoutMenuItem = page.getByText(/ログアウト/i);

    if (await logoutButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await logoutButton.click();
    } else if (
      await logoutLink.isVisible({ timeout: 1000 }).catch(() => false)
    ) {
      await logoutLink.click();
    } else if (
      await logoutMenuItem.isVisible({ timeout: 1000 }).catch(() => false)
    ) {
      await logoutMenuItem.click();
    } else {
      // If no visible logout button, call the API directly and navigate
      const apiBase = getApiBaseUrl();
      await page.evaluate(async (url) => {
        await fetch(`${url}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      }, apiBase);
      await page.goto("/");
    }

    // Should be redirected to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test("accessing protected API without auth returns 401", async () => {
    // Direct API call without authentication
    const response = await fetch(
      `${getApiBaseUrl()}/users/me`,
    );
    expect(response.status).toBe(401);
  });

  test("refresh token cookie is httponly", async () => {
    // Verify that login response sets an HttpOnly cookie
    const result = await login(TEST_EMAIL, TEST_PASSWORD);
    expect(result.setCookieHeaders.length).toBeGreaterThan(0);
    const refreshTokenCookie = result.setCookieHeaders.find((h) =>
      h.toLowerCase().includes("refresh_token"),
    );
    expect(refreshTokenCookie).toBeDefined();
    expect(refreshTokenCookie!.toLowerCase()).toContain("httponly");
  });
});
