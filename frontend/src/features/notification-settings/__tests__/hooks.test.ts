import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockGet = vi.fn();
const mockPut = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
      put: (...args: unknown[]) => mockPut(...args),
    },
  };
});

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    userId: "00000000-0000-0000-0000-000000000001",
    name: "Dev User",
  }),
}));

const TEST_USER_ID = "00000000-0000-0000-0000-000000000001";

beforeEach(() => {
  vi.clearAllMocks();
});

// -- useNotificationSetting ---------------------------------------------------

describe("useNotificationSetting", () => {
  it("fetches notification setting on mount and returns data", async () => {
    const mockSetting = {
      user_id: TEST_USER_ID,
      reminder_minutes_before: 30,
      is_enabled: true,
    };
    mockGet.mockResolvedValueOnce(mockSetting);

    const { useNotificationSetting } =
      await import("../hooks/useNotificationSetting");
    const { result } = renderHook(() => useNotificationSetting());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith(
      "/notification-settings",
      TEST_USER_ID,
    );
    expect(result.current.setting).toEqual(mockSetting);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(500, "Server Error", {}));

    const { useNotificationSetting } =
      await import("../hooks/useNotificationSetting");
    const { result } = renderHook(() => useNotificationSetting());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.setting).toBeNull();
    expect(result.current.error).toBe("通知設定の取得に失敗しました (500)");
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { useNotificationSetting } =
      await import("../hooks/useNotificationSetting");
    const { result } = renderHook(() => useNotificationSetting());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("通知設定の取得に失敗しました");
  });

  it("refetch reloads the data", async () => {
    const mockSetting = {
      user_id: TEST_USER_ID,
      reminder_minutes_before: 30,
      is_enabled: true,
    };
    mockGet.mockResolvedValue(mockSetting);

    const { useNotificationSetting } =
      await import("../hooks/useNotificationSetting");
    const { result } = renderHook(() => useNotificationSetting());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.refetch();
    });

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(2);
    });
  });
});

// -- useUpdateNotificationSetting ---------------------------------------------

describe("useUpdateNotificationSetting", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = {
      user_id: TEST_USER_ID,
      reminder_minutes_before: 15,
      is_enabled: false,
    };
    mockPut.mockResolvedValueOnce(mockResponse);

    const { useUpdateNotificationSetting } =
      await import("../hooks/useUpdateNotificationSetting");
    const { result } = renderHook(() => useUpdateNotificationSetting());

    let response: unknown;
    await act(async () => {
      response = await result.current.updateSetting({
        reminder_minutes_before: 15,
        is_enabled: false,
      });
    });

    expect(mockPut).toHaveBeenCalledWith(
      "/notification-settings",
      TEST_USER_ID,
      { reminder_minutes_before: 15, is_enabled: false },
    );
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPut.mockRejectedValueOnce(
      new ApiError(422, "Unprocessable Entity", {}),
    );

    const { useUpdateNotificationSetting } =
      await import("../hooks/useUpdateNotificationSetting");
    const { result } = renderHook(() => useUpdateNotificationSetting());

    let response: unknown;
    await act(async () => {
      response = await result.current.updateSetting({
        reminder_minutes_before: 3,
        is_enabled: true,
      });
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("通知設定の更新に失敗しました (422)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPut.mockRejectedValueOnce(new Error("network"));

    const { useUpdateNotificationSetting } =
      await import("../hooks/useUpdateNotificationSetting");
    const { result } = renderHook(() => useUpdateNotificationSetting());

    await act(async () => {
      await result.current.updateSetting({
        reminder_minutes_before: 30,
        is_enabled: true,
      });
    });

    expect(result.current.error).toBe("通知設定の更新に失敗しました");
  });
});
