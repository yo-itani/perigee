/**
 * Authentication helper for E2E tests.
 *
 * Handles login via the backend API and saves the browser storageState
 * (cookies) so that authenticated tests can restore the session without
 * logging in again through the UI.
 */

import { type BrowserContext, type Page } from "@playwright/test";
import { login } from "./api.helper";

const AUTH_STATE_DIR = "e2e/.auth";

export interface AuthUser {
  email: string;
  password: string;
  storageStatePath: string;
}

export const ADMIN_USER: AuthUser = {
  email: "admin@e2e-test.example.com",
  password: "e2e-admin-password-123",
  storageStatePath: `${AUTH_STATE_DIR}/admin.json`,
};

/**
 * Login via the API and persist the refresh token cookie into a storageState file.
 *
 * The flow:
 * 1. Call POST /auth/login to get the access token and Set-Cookie header
 * 2. Navigate the page to the base URL so we can set the cookie on the correct domain
 * 3. Set the refresh_token cookie from the API response
 * 4. Save the storageState to disk
 */
export async function loginAndSaveState(
  page: Page,
  context: BrowserContext,
  user: AuthUser,
): Promise<void> {
  const result = await login(user.email, user.password);

  // Parse the refresh_token cookie from Set-Cookie headers
  if (result.setCookieHeaders.length === 0) {
    throw new Error("No Set-Cookie header in login response");
  }

  const refreshCookie = result.setCookieHeaders.find((h) =>
    h.startsWith("refresh_token="),
  );
  if (!refreshCookie) {
    throw new Error(
      "refresh_token cookie not found in Set-Cookie headers",
    );
  }

  const cookieAttrs = parseCookieHeader(refreshCookie);

  // Navigate to the app to establish the cookie domain
  const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:5174";
  const apiBaseURL = process.env.E2E_API_BASE_URL ?? "http://localhost:8001";
  const apiUrl = new URL(apiBaseURL);

  await page.goto(baseURL);

  // Set the cookie on the API domain (for /auth path)
  await context.addCookies([
    {
      name: "refresh_token",
      value: cookieAttrs.value,
      domain: apiUrl.hostname,
      path: cookieAttrs.path ?? "/auth",
      httpOnly: cookieAttrs.httpOnly ?? true,
      secure: cookieAttrs.secure ?? false,
      sameSite: (cookieAttrs.sameSite as "Lax" | "Strict" | "None") ?? "Lax",
    },
  ]);

  // Save the storageState (includes cookies)
  await context.storageState({ path: user.storageStatePath });
}

interface CookieAttributes {
  value: string;
  path?: string;
  httpOnly?: boolean;
  secure?: boolean;
  sameSite?: string;
}

function parseCookieHeader(setCookieHeader: string): CookieAttributes {
  const parts = setCookieHeader.split(";").map((p) => p.trim());
  const [nameValue, ...attrs] = parts;
  const eqIdx = nameValue.indexOf("=");
  const value = eqIdx >= 0 ? nameValue.substring(eqIdx + 1) : nameValue;

  const result: CookieAttributes = { value };
  for (const attr of attrs) {
    const lower = attr.toLowerCase();
    if (lower === "httponly") {
      result.httpOnly = true;
    } else if (lower === "secure") {
      result.secure = true;
    } else if (lower.startsWith("path=")) {
      result.path = attr.substring(5);
    } else if (lower.startsWith("samesite=")) {
      result.sameSite = attr.substring(9);
    }
  }
  return result;
}
