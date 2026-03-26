import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockPut = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      put: (...args: unknown[]) => mockPut(...args),
      delete: vi.fn(),
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

// -- useUpdateMemo ------------------------------------------------------------

describe("useUpdateMemo", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { record_id: "r1" };
    mockPut.mockResolvedValueOnce(mockResponse);

    const { useUpdateMemo } = await import("../useUpdateMemo");
    const { result } = renderHook(() => useUpdateMemo("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.updateMemo("Updated memo");
    });

    expect(mockPut).toHaveBeenCalledWith("/records/r1/memo", TEST_USER_ID, {
      memo: "Updated memo",
    });
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPut.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useUpdateMemo } = await import("../useUpdateMemo");
    const { result } = renderHook(() => useUpdateMemo("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.updateMemo("Bad memo");
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("メモの保存に失敗しました (400)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPut.mockRejectedValueOnce(new Error("network"));

    const { useUpdateMemo } = await import("../useUpdateMemo");
    const { result } = renderHook(() => useUpdateMemo("r1"));

    await act(async () => {
      await result.current.updateMemo("memo");
    });

    expect(result.current.error).toBe("メモの保存に失敗しました");
  });
});
