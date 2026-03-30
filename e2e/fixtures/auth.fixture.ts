/**
 * Custom Playwright fixture that provides an authenticated page.
 *
 * Uses the storageState saved during the global setup phase to restore
 * the admin user's session (HttpOnly refresh token cookie).
 * On page load, the AuthGuard component will use the cookie to obtain
 * a fresh access token via POST /auth/refresh.
 */

import { test as base, type Page } from "@playwright/test";
import { ADMIN_USER } from "../helpers/auth.helper";

type AuthFixtures = {
  /** A page that is already authenticated as the admin user. */
  authenticatedPage: Page;
};

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: ADMIN_USER.storageStatePath,
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
});

export { expect } from "@playwright/test";
