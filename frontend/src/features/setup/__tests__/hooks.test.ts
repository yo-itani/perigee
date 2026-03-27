import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

// -- Mock setup ---------------------------------------------------------------

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock import.meta.env
vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");

beforeEach(() => {
  vi.clearAllMocks();
});

// -- useSystemStatus ----------------------------------------------------------

describe("useSystemStatus", () => {
  it("returns isSetupComplete=false when no users exist", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ is_setup_complete: false }),
    });

    const { useSystemStatus } = await import("../hooks/useSystemStatus");
    const { result } = renderHook(() => useSystemStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSetupComplete).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("returns isSetupComplete=true when users exist", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ is_setup_complete: true }),
    });

    const { useSystemStatus } = await import("../hooks/useSystemStatus");
    const { result } = renderHook(() => useSystemStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSetupComplete).toBe(true);
  });

  it("sets error when API call fails", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Server Error",
    });

    const { useSystemStatus } = await import("../hooks/useSystemStatus");
    const { result } = renderHook(() => useSystemStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSetupComplete).toBeNull();
    expect(result.current.error).toBe(
      "システムステータスの取得に失敗しました (500)",
    );
  });

  it("sets generic error on network failure", async () => {
    mockFetch.mockRejectedValueOnce(new Error("network failure"));

    const { useSystemStatus } = await import("../hooks/useSystemStatus");
    const { result } = renderHook(() => useSystemStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("システムステータスの取得に失敗しました");
  });

  it("refetch reloads the data", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ is_setup_complete: false }),
    });

    const { useSystemStatus } = await import("../hooks/useSystemStatus");
    const { result } = renderHook(() => useSystemStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.refetch();
    });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });
});

// -- useSetupFirstUser --------------------------------------------------------

describe("useSetupFirstUser", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = {
      id: "00000000-0000-0000-0000-000000000001",
      name: "Admin",
      email: "admin@example.com",
      role: "admin",
      is_active: true,
      slack_user_id: null,
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const { useSetupFirstUser } = await import("../hooks/useSetupFirstUser");
    const { result } = renderHook(() => useSetupFirstUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.setupUser({
        name: "Admin",
        email: "admin@example.com",
      });
    });

    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
    expect(result.current.isSubmitting).toBe(false);
  });

  it("sets error on 409 conflict (already setup)", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      statusText: "Conflict",
      json: async () => ({ detail: "Setup is already complete." }),
    });

    const { useSetupFirstUser } = await import("../hooks/useSetupFirstUser");
    const { result } = renderHook(() => useSetupFirstUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.setupUser({
        name: "Admin",
        email: "admin@example.com",
      });
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("セットアップは既に完了しています");
  });

  it("sets generic error on non-ApiError", async () => {
    mockFetch.mockRejectedValueOnce(new Error("network"));

    const { useSetupFirstUser } = await import("../hooks/useSetupFirstUser");
    const { result } = renderHook(() => useSetupFirstUser());

    await act(async () => {
      await result.current.setupUser({
        name: "Admin",
        email: "admin@example.com",
      });
    });

    expect(result.current.error).toBe("ユーザー登録に失敗しました");
  });

  it("sets error with status code on other API errors", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: async () => ({ detail: "Validation error" }),
    });

    const { useSetupFirstUser } = await import("../hooks/useSetupFirstUser");
    const { result } = renderHook(() => useSetupFirstUser());

    await act(async () => {
      await result.current.setupUser({
        name: "Admin",
        email: "bad-email",
      });
    });

    expect(result.current.error).toBe("ユーザー登録に失敗しました (422)");
  });
});
