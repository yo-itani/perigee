import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockPost = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
      post: (...args: unknown[]) => mockPost(...args),
      put: vi.fn(),
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

// -- useSaveDraft -------------------------------------------------------------

describe("useSaveDraft", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { record_id: "r1" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { useSaveDraft } = await import("../useSaveDraft");
    const { result } = renderHook(() => useSaveDraft("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.saveDraft();
    });

    expect(mockPost).toHaveBeenCalledWith(
      "/records/r1/save-draft",
      TEST_USER_ID,
    );
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useSaveDraft } = await import("../useSaveDraft");
    const { result } = renderHook(() => useSaveDraft("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.saveDraft();
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("下書き保存に失敗しました (400)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { useSaveDraft } = await import("../useSaveDraft");
    const { result } = renderHook(() => useSaveDraft("r1"));

    await act(async () => {
      await result.current.saveDraft();
    });

    expect(result.current.error).toBe("下書き保存に失敗しました");
  });
});
