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

function buildHeaders(userId: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-User-Id": userId,
  };
}

export const apiClient = {
  async get<T>(path: string, userId: string): Promise<T> {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      method: "GET",
      headers: buildHeaders(userId),
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, userId: string, body?: unknown): Promise<T> {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      method: "POST",
      headers: buildHeaders(userId),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async put<T>(path: string, userId: string, body?: unknown): Promise<T> {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      method: "PUT",
      headers: buildHeaders(userId),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async delete<T>(path: string, userId: string): Promise<T> {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      method: "DELETE",
      headers: buildHeaders(userId),
    });
    return handleResponse<T>(response);
  },
};
