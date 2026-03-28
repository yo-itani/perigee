/**
 * In-memory store for the access token.
 * The token is never persisted to localStorage or cookies.
 * Refresh tokens are handled via HttpOnly cookies by the server.
 */

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}
