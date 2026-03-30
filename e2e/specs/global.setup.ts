/**
 * Global setup for E2E tests.
 *
 * Runs as a Playwright project dependency before all other test projects.
 * Responsibilities:
 * 1. Reset the test database via POST /test/reset
 * 2. Run initial system setup (create admin user)
 * 3. Login as admin and save storageState for authenticated tests
 */

import { test as setup } from "@playwright/test";
import { resetDatabase, setupFirstUser } from "../helpers/api.helper";
import { ADMIN_USER, loginAndSaveState } from "../helpers/auth.helper";

setup("reset database and create admin user", async ({ page, context }) => {
  // 1. Reset the test database
  await resetDatabase();

  // 2. Create admin user via system setup
  const result = await setupFirstUser({
    name: "E2E Admin",
    email: ADMIN_USER.email,
    password: ADMIN_USER.password,
  });

  if (result.status !== 201) {
    throw new Error(
      `Failed to create admin user: ${result.status} ${JSON.stringify(result.data)}`,
    );
  }

  // 3. Login and save storageState
  await loginAndSaveState(page, context, ADMIN_USER);
});
