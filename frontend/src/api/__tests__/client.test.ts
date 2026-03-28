import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiClient, ApiError } from "../client";
import * as authStore from "../auth-store";
import * as auth from "../auth";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// Prevent actual navigation in tests
const originalLocation = window.location;

beforeEach(() => {
  authStore.clearAccessToken();
  fetchMock.mockReset();
  vi.restoreAllMocks();
  Object.defineProperty(window, "location", {
    writable: true,
    value: { ...originalLocation, href: "" },
  });
});

afterEach(() => {
  Object.defineProperty(window, "location", {
    writable: true,
    value: originalLocation,
  });
});

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    headers: new Headers(),
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("apiClient", () => {
  it("sends Authorization header when token is set", async () => {
    authStore.setAccessToken("test-token");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { data: 1 }));

    await apiClient.get("/test");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["Authorization"]).toBe(
      "Bearer test-token",
    );
  });

  it("sends credentials: include", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { data: 1 }));

    await apiClient.get("/test");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe("include");
  });

  it("throws ApiError on non-401 error", async () => {
    authStore.setAccessToken("test-token");
    fetchMock.mockResolvedValueOnce(jsonResponse(403, { detail: "Forbidden" }));

    await expect(apiClient.get("/test")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("401 → refresh → retry flow", () => {
  it("retries request after successful refresh", async () => {
    authStore.setAccessToken("old-token");

    // First call → 401
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: "expired" }));
    // refreshApi call (mocked below)
    vi.spyOn(auth, "refreshApi").mockResolvedValueOnce({
      access_token: "new-token",
      token_type: "bearer",
    });
    // Retry call → 200
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    const result = await apiClient.get<{ ok: boolean }>("/test");

    expect(result).toEqual({ ok: true });
    expect(authStore.getAccessToken()).toBe("new-token");
  });

  it("redirects to /login when refresh fails", async () => {
    authStore.setAccessToken("old-token");

    // First call → 401
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: "expired" }));
    // refreshApi fails
    vi.spyOn(auth, "refreshApi").mockRejectedValueOnce(
      new auth.RefreshError(401),
    );

    await expect(apiClient.get("/test")).rejects.toBeInstanceOf(ApiError);
    expect(authStore.getAccessToken()).toBeNull();
    expect(window.location.href).toBe("/login");
  });

  it("deduplicates concurrent refresh attempts", async () => {
    authStore.setAccessToken("old-token");

    // Use a deferred promise to control refresh timing so both 401s
    // hit tryRefresh before it resolves.
    let resolveRefresh!: (v: auth.RefreshResponse) => void;
    const refreshPromise = new Promise<auth.RefreshResponse>((r) => {
      resolveRefresh = r;
    });
    const refreshSpy = vi
      .spyOn(auth, "refreshApi")
      .mockReturnValue(refreshPromise);

    // Both calls return 401
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: "expired" }));
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: "expired" }));
    // Both retry calls return 200
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { a: 1 }));
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { b: 2 }));

    const p1 = apiClient.get("/a");
    const p2 = apiClient.get("/b");

    // Let microtasks run so both requests hit the 401 path
    await vi.waitFor(() => expect(refreshSpy).toHaveBeenCalled());

    // Now resolve the single shared refresh
    resolveRefresh({ access_token: "new-token", token_type: "bearer" });

    const [r1, r2] = await Promise.all([p1, p2]);

    expect(r1).toEqual({ a: 1 });
    expect(r2).toEqual({ b: 2 });
    // refreshApi should only be called once despite two 401s
    expect(refreshSpy).toHaveBeenCalledTimes(1);
  });
});
