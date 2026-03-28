/**
 * Authentication API functions.
 * These bypass the main apiClient because they have different auth requirements.
 */

const DEFAULT_BASE_URL = "http://localhost:8000";

function getBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

export interface SetPasswordResponse {
  message: string;
}

export async function loginApi(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await fetch(`${getBaseUrl()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let detail = "ログインに失敗しました";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // ignore parse error
    }
    throw new LoginError(response.status, detail);
  }

  return (await response.json()) as LoginResponse;
}

export async function refreshApi(): Promise<RefreshResponse> {
  const response = await fetch(`${getBaseUrl()}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new RefreshError(response.status);
  }

  return (await response.json()) as RefreshResponse;
}

export async function logoutApi(): Promise<void> {
  await fetch(`${getBaseUrl()}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function setPasswordApi(
  token: string,
  password: string,
): Promise<SetPasswordResponse> {
  const response = await fetch(`${getBaseUrl()}/auth/set-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ token, password }),
  });

  if (!response.ok) {
    let detail = "パスワードの設定に失敗しました";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // ignore parse error
    }
    throw new SetPasswordError(response.status, detail);
  }

  return (await response.json()) as SetPasswordResponse;
}

export class LoginError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "LoginError";
  }
}

export class RefreshError extends Error {
  constructor(public readonly status: number) {
    super(`Refresh failed with status ${status}`);
    this.name = "RefreshError";
  }
}

export class SetPasswordError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "SetPasswordError";
  }
}
