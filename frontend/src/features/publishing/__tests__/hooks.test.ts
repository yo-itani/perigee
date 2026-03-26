import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
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

// -- useSuggestedViewers ------------------------------------------------------

describe("useSuggestedViewers", () => {
  it("fetches suggested viewers on mount and returns data", async () => {
    const mockResponse = {
      suggested_viewer_ids: ["viewer1", "viewer2"],
    };
    mockGet.mockResolvedValueOnce(mockResponse);

    const { useSuggestedViewers } =
      await import("../hooks/useSuggestedViewers");
    const { result } = renderHook(() => useSuggestedViewers("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith(
      "/records/r1/suggested-viewers",
      TEST_USER_ID,
    );
    expect(result.current.suggestedViewerIds).toEqual(["viewer1", "viewer2"]);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(404, "Not Found", {}));

    const { useSuggestedViewers } =
      await import("../hooks/useSuggestedViewers");
    const { result } = renderHook(() => useSuggestedViewers("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.suggestedViewerIds).toEqual([]);
    expect(result.current.error).toBe(
      "公開先サジェストの取得に失敗しました (404)",
    );
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { useSuggestedViewers } =
      await import("../hooks/useSuggestedViewers");
    const { result } = renderHook(() => useSuggestedViewers("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("公開先サジェストの取得に失敗しました");
  });
});

// -- useSetViewers ------------------------------------------------------------

describe("useSetViewers", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { record_id: "r1" };
    mockPut.mockResolvedValueOnce(mockResponse);

    const { useSetViewers } = await import("../hooks/useSetViewers");
    const { result } = renderHook(() => useSetViewers("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.setViewers(["v1", "v2"]);
    });

    expect(mockPut).toHaveBeenCalledWith("/records/r1/viewers", TEST_USER_ID, {
      viewer_ids: ["v1", "v2"],
    });
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPut.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useSetViewers } = await import("../hooks/useSetViewers");
    const { result } = renderHook(() => useSetViewers("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.setViewers(["v1"]);
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("公開先の設定に失敗しました (400)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPut.mockRejectedValueOnce(new Error("network"));

    const { useSetViewers } = await import("../hooks/useSetViewers");
    const { result } = renderHook(() => useSetViewers("r1"));

    await act(async () => {
      await result.current.setViewers(["v1"]);
    });

    expect(result.current.error).toBe("公開先の設定に失敗しました");
  });
});

// -- usePublishRecord ---------------------------------------------------------

describe("usePublishRecord", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { record_id: "r1" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { usePublishRecord } = await import("../hooks/usePublishRecord");
    const { result } = renderHook(() => usePublishRecord("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.publishRecord(["v1", "v2"]);
    });

    expect(mockPost).toHaveBeenCalledWith("/records/r1/publish", TEST_USER_ID, {
      viewer_ids: ["v1", "v2"],
    });
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { usePublishRecord } = await import("../hooks/usePublishRecord");
    const { result } = renderHook(() => usePublishRecord("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.publishRecord(["v1"]);
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("記録の公開に失敗しました (400)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { usePublishRecord } = await import("../hooks/usePublishRecord");
    const { result } = renderHook(() => usePublishRecord("r1"));

    await act(async () => {
      await result.current.publishRecord(["v1"]);
    });

    expect(result.current.error).toBe("記録の公開に失敗しました");
  });
});
