import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
    },
  };
});

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    user: {
      userId: "00000000-0000-0000-0000-000000000001",
      name: "Dev User",
      email: "test@example.com",
      role: "admin",
      isActive: true,
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

// -- useRecordDetail ----------------------------------------------------------

describe("useRecordDetail", () => {
  it("fetches record detail on mount and returns data", async () => {
    const mockRecord = {
      record_id: "r1",
      organizer_id: "org1",
      counterpart_id: "cp1",
      schedule_id: null,
      memo: "Test memo",
      status: "published",
      confirmed_agenda_ids: ["a1"],
      action_items: [],
      conducted_at: "2026-04-01T10:00:00Z",
      created_at: "2026-03-20T10:00:00Z",
      updated_at: "2026-03-20T10:00:00Z",
    };
    mockGet.mockResolvedValueOnce(mockRecord);

    const { useRecordDetail } = await import("../hooks/useRecordDetail");
    const { result } = renderHook(() => useRecordDetail("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith("/records/r1");
    expect(result.current.record).toEqual(mockRecord);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(404, "Not Found", {}));

    const { useRecordDetail } = await import("../hooks/useRecordDetail");
    const { result } = renderHook(() => useRecordDetail("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.record).toBeNull();
    expect(result.current.error).toBe("記録の取得に失敗しました (404)");
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { useRecordDetail } = await import("../hooks/useRecordDetail");
    const { result } = renderHook(() => useRecordDetail("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("記録の取得に失敗しました");
  });
});

// -- useRecordComments --------------------------------------------------------

describe("useRecordComments", () => {
  it("fetches comments on mount and returns data", async () => {
    const mockComments = {
      comments: [
        {
          comment_id: "c1",
          author_id: "user1",
          body: "Great session!",
          created_at: "2026-04-02T10:00:00Z",
        },
      ],
    };
    mockGet.mockResolvedValueOnce(mockComments);

    const { useRecordComments } = await import("../hooks/useRecordComments");
    const { result } = renderHook(() => useRecordComments("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith("/records/r1/comments");
    expect(result.current.comments).toEqual(mockComments.comments);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(500, "Server Error", {}));

    const { useRecordComments } = await import("../hooks/useRecordComments");
    const { result } = renderHook(() => useRecordComments("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.comments).toEqual([]);
    expect(result.current.error).toBe("コメントの取得に失敗しました (500)");
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { useRecordComments } = await import("../hooks/useRecordComments");
    const { result } = renderHook(() => useRecordComments("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("コメントの取得に失敗しました");
  });
});

// -- useRecordViewers ---------------------------------------------------------

describe("useRecordViewers", () => {
  it("fetches viewers on mount and returns data", async () => {
    const mockViewers = {
      viewer_ids: ["viewer1", "viewer2"],
    };
    mockGet.mockResolvedValueOnce(mockViewers);

    const { useRecordViewers } = await import("../hooks/useRecordViewers");
    const { result } = renderHook(() => useRecordViewers("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith("/records/r1/viewers");
    expect(result.current.viewerIds).toEqual(["viewer1", "viewer2"]);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(403, "Forbidden", {}));

    const { useRecordViewers } = await import("../hooks/useRecordViewers");
    const { result } = renderHook(() => useRecordViewers("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.viewerIds).toEqual([]);
    expect(result.current.error).toBe("公開先の取得に失敗しました (403)");
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { useRecordViewers } = await import("../hooks/useRecordViewers");
    const { result } = renderHook(() => useRecordViewers("r1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("公開先の取得に失敗しました");
  });
});

// -- useAddRecordComment ------------------------------------------------------

describe("useAddRecordComment", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { comment_id: "c-new" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { useAddRecordComment } =
      await import("../hooks/useAddRecordComment");
    const { result } = renderHook(() => useAddRecordComment("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.addComment("Nice work!");
    });

    expect(mockPost).toHaveBeenCalledWith("/records/r1/comments", {
      body: "Nice work!",
    });
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(422, "Unprocessable", {}));

    const { useAddRecordComment } =
      await import("../hooks/useAddRecordComment");
    const { result } = renderHook(() => useAddRecordComment("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.addComment("");
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("コメントの追加に失敗しました (422)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { useAddRecordComment } =
      await import("../hooks/useAddRecordComment");
    const { result } = renderHook(() => useAddRecordComment("r1"));

    await act(async () => {
      await result.current.addComment("body");
    });

    expect(result.current.error).toBe("コメントの追加に失敗しました");
  });
});

// -- useCompleteActionItem ----------------------------------------------------

describe("useCompleteActionItem", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { action_item_id: "ai1" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { useCompleteActionItem } =
      await import("../hooks/useCompleteActionItem");
    const { result } = renderHook(() => useCompleteActionItem());

    let response: unknown;
    await act(async () => {
      response = await result.current.completeItem("ai1");
    });

    expect(mockPost).toHaveBeenCalledWith("/action-items/ai1/complete");
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useCompleteActionItem } =
      await import("../hooks/useCompleteActionItem");
    const { result } = renderHook(() => useCompleteActionItem());

    let response: unknown;
    await act(async () => {
      response = await result.current.completeItem("ai1");
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe(
      "アクションアイテムの完了に失敗しました (400)",
    );
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { useCompleteActionItem } =
      await import("../hooks/useCompleteActionItem");
    const { result } = renderHook(() => useCompleteActionItem());

    await act(async () => {
      await result.current.completeItem("ai1");
    });

    expect(result.current.error).toBe("アクションアイテムの完了に失敗しました");
  });
});
