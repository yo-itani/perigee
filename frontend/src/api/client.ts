import { getAccessToken, setAccessToken, clearAccessToken } from "./auth-store";
import { refreshApi, RefreshError } from "./auth";

const DEFAULT_BASE_URL = "http://localhost:8000";

function getBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly statusText: string,
    public readonly body: unknown,
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = await response.text();
    }
    throw new ApiError(response.status, response.statusText, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function buildHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Singleton guard to prevent concurrent refresh attempts.
 * When a 401 triggers a refresh, all parallel requests wait on the same promise.
 */
let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) {
    return refreshPromise;
  }
  refreshPromise = (async () => {
    try {
      const result = await refreshApi();
      setAccessToken(result.access_token);
      return true;
    } catch (e) {
      if (e instanceof RefreshError) {
        clearAccessToken();
        return false;
      }
      clearAccessToken();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function fetchWithAuth<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...init,
    headers: buildHeaders(),
    credentials: "include",
  });

  if (response.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      // Retry with new token
      const retryResponse = await fetch(`${getBaseUrl()}${path}`, {
        ...init,
        headers: buildHeaders(),
        credentials: "include",
      });
      return handleResponse<T>(retryResponse);
    }
    // Refresh failed - redirect to login
    window.location.href = "/login";
    throw new ApiError(401, "Unauthorized", null);
  }

  return handleResponse<T>(response);
}

export const apiClient = {
  async get<T>(path: string): Promise<T> {
    return fetchWithAuth<T>(path, { method: "GET" });
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    return fetchWithAuth<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  async put<T>(path: string, body?: unknown): Promise<T> {
    return fetchWithAuth<T>(path, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  async delete<T>(path: string): Promise<T> {
    return fetchWithAuth<T>(path, { method: "DELETE" });
  },
};
