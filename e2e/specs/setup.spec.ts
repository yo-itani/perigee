/**
 * E2E tests for the initial setup flow.
 *
 * Tests the system setup page that appears when no users exist,
 * verifying the full flow: setup page -> register admin -> redirect to login.
 */

import { test, expect } from "@playwright/test";
import { resetDatabase, getSystemStatus } from "../helpers/api.helper";

test.describe("Initial setup flow", () => {
  test.beforeEach(async () => {
    // Reset DB to ensure no users exist
    await resetDatabase();
  });

  test("shows setup page when system is not initialized", async ({ page }) => {
    const status = await getSystemStatus();
    expect(status.is_setup_complete).toBe(false);

    await page.goto("/");

    // SetupGuard should redirect to /setup
    await expect(page).toHaveURL(/\/setup/);
    await expect(
      page.getByRole("heading", { name: "初期セットアップ" }),
    ).toBeVisible();
  });

  test("completes setup and redirects to login", async ({ page }) => {
    await page.goto("/setup");

    await expect(
      page.getByRole("heading", { name: "初期セットアップ" }),
    ).toBeVisible();

    // Fill in the admin user form
    await page.getByLabel("名前").fill("E2E Setup Admin");
    await page.getByLabel("メールアドレス").fill("setup-admin@e2e-test.example.com");
    await page.getByLabel("パスワード").fill("setup-password-123");

    // Submit the form
    await page.getByRole("button", { name: "登録" }).click();

    // Should redirect to login page
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
    await expect(
      page.getByRole("heading", { name: "ログイン" }),
    ).toBeVisible();
  });

  test("shows validation error for empty name", async ({ page }) => {
    await page.goto("/setup");

    await expect(
      page.getByRole("heading", { name: "初期セットアップ" }),
    ).toBeVisible();

    // Leave name empty, fill other fields
    await page.getByLabel("メールアドレス").fill("test@e2e-test.example.com");
    await page.getByLabel("パスワード").fill("test-password-123");

    await page.getByRole("button", { name: "登録" }).click();

    // Should show validation error
    await expect(page.getByText("名前を入力してください")).toBeVisible();
  });

  test("shows validation error for short password", async ({ page }) => {
    await page.goto("/setup");

    await page.getByLabel("名前").fill("Test User");
    await page.getByLabel("メールアドレス").fill("test@e2e-test.example.com");
    await page.getByLabel("パスワード").fill("short");

    await page.getByRole("button", { name: "登録" }).click();

    await expect(
      page.getByText("パスワードは8文字以上で入力してください"),
    ).toBeVisible();
  });

  test("redirects away from setup when already initialized", async ({
    page,
  }) => {
    // First, set up the system
    const { setupFirstUser } = await import("../helpers/api.helper");
    await setupFirstUser({
      name: "Already Setup",
      email: "already@e2e-test.example.com",
      password: "password-123456",
    });

    // Now visit /setup — should redirect to /
    await page.goto("/setup");

    // SetupPage checks system status and redirects if setup is complete
    await expect(page).not.toHaveURL(/\/setup/, { timeout: 10000 });
  });
});
