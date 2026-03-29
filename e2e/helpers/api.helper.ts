/**
 * Backend API direct-call helper for E2E test data setup.
 *
 * Uses fetch (no browser context needed) to call the backend API directly.
 * This is used for test data creation instead of going through the UI.
 */

const DEFAULT_API_BASE_URL = "http://localhost:8000";

function getApiBaseUrl(): string {
  return process.env.E2E_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export interface ApiResponse<T> {
  status: number;
  data: T;
}

/**
 * Make a JSON request to the backend API.
 */
async function apiRequest<T>(
  method: string,
  path: string,
  options?: {
    body?: Record<string, unknown>;
    headers?: Record<string, string>;
    cookie?: string;
  },
): Promise<ApiResponse<T>> {
  const url = `${getApiBaseUrl()}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options?.headers,
  };
  if (options?.cookie) {
    headers["Cookie"] = options.cookie;
  }

  const response = await fetch(url, {
    method,
    headers,
    body: options?.body ? JSON.stringify(options.body) : undefined,
  });

  let data: T;
  if (
    response.status === 204 ||
    !response.headers.get("content-type")?.includes("application/json")
  ) {
    data = {} as T;
  } else {
    data = (await response.json()) as T;
  }

  return { status: response.status, data };
}

/**
 * Check system setup status.
 */
export async function getSystemStatus(): Promise<{
  is_setup_complete: boolean;
}> {
  const res = await apiRequest<{ is_setup_complete: boolean }>(
    "GET",
    "/system/status",
  );
  return res.data;
}

/**
 * Register the first admin user via the system setup endpoint.
 */
export async function setupFirstUser(params: {
  name: string;
  email: string;
  password: string;
}): Promise<
  ApiResponse<{
    id: string;
    name: string;
    email: string;
    role: string;
    is_active: boolean;
    slack_user_id: string | null;
  }>
> {
  return apiRequest("POST", "/system/setup", { body: params });
}

/**
 * Login and return the response including Set-Cookie headers.
 */
export async function login(
  email: string,
  password: string,
): Promise<{
  accessToken: string;
  setCookieHeader: string | null;
}> {
  const url = `${getApiBaseUrl()}/auth/login`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    redirect: "manual",
  });

  if (!response.ok) {
    throw new Error(`Login failed with status ${response.status}`);
  }

  const body = (await response.json()) as { access_token: string };
  const setCookieHeader = response.headers.get("set-cookie");

  return {
    accessToken: body.access_token,
    setCookieHeader,
  };
}

/**
 * Reset the test database (E2E only).
 * Requires PERIGEE_ENABLE_TEST_ENDPOINTS=true and perigee_e2e* DB.
 */
export async function resetDatabase(): Promise<void> {
  const res = await apiRequest("POST", "/test/reset");
  if (res.status !== 204) {
    throw new Error(`Database reset failed with status ${res.status}`);
  }
}
