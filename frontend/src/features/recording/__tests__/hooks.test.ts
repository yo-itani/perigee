import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
      put: (...args: unknown[]) => mockPut(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
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

// -- useRecordDetail ----------------------------------------------------------

describe("useRecordDetail", () => {
  it("fetches record detail on mount and returns data", async () => {
    const mockRecord = {
      record_id: "r1",
      organizer_id: "org1",
      counterpart_id: "cp1",
      schedule_id: "s1",
      memo: "test memo",
      status: "draft",
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

    expect(mockGet).toHaveBeenCalledWith("/records/r1", TEST_USER_ID);
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

// -- useConfirmAgenda ---------------------------------------------------------

describe("useConfirmAgenda", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { record_id: "r1", agenda_id: "a1" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { useConfirmAgenda } = await import("../hooks/useConfirmAgenda");
    const { result } = renderHook(() => useConfirmAgenda("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.confirmAgenda("a1");
    });

    expect(mockPost).toHaveBeenCalledWith(
      "/records/r1/agendas/a1/confirm",
      TEST_USER_ID,
    );
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useConfirmAgenda } = await import("../hooks/useConfirmAgenda");
    const { result } = renderHook(() => useConfirmAgenda("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.confirmAgenda("a1");
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("アジェンダの確認に失敗しました (400)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { useConfirmAgenda } = await import("../hooks/useConfirmAgenda");
    const { result } = renderHook(() => useConfirmAgenda("r1"));

    await act(async () => {
      await result.current.confirmAgenda("a1");
    });

    expect(result.current.error).toBe("アジェンダの確認に失敗しました");
  });
});

// -- useAddActionItem ---------------------------------------------------------

describe("useAddActionItem", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { action_item_id: "ai-new" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { useAddActionItem } = await import("../hooks/useAddActionItem");
    const { result } = renderHook(() => useAddActionItem("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.addActionItem("New action");
    });

    expect(mockPost).toHaveBeenCalledWith(
      "/records/r1/action-items",
      TEST_USER_ID,
      { title: "New action" },
    );
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useAddActionItem } = await import("../hooks/useAddActionItem");
    const { result } = renderHook(() => useAddActionItem("r1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.addActionItem("Bad action");
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe(
      "アクションアイテムの追加に失敗しました (400)",
    );
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { useAddActionItem } = await import("../hooks/useAddActionItem");
    const { result } = renderHook(() => useAddActionItem("r1"));

    await act(async () => {
      await result.current.addActionItem("action");
    });

    expect(result.current.error).toBe("アクションアイテムの追加に失敗しました");
  });
});

// -- useDeleteActionItem ------------------------------------------------------

describe("useDeleteActionItem", () => {
  it("calls API and returns true on success", async () => {
    mockDelete.mockResolvedValueOnce(undefined);

    const { useDeleteActionItem } =
      await import("../hooks/useDeleteActionItem");
    const { result } = renderHook(() => useDeleteActionItem("r1"));

    let success: boolean | undefined;
    await act(async () => {
      success = await result.current.deleteActionItem("ai1");
    });

    expect(mockDelete).toHaveBeenCalledWith(
      "/records/r1/action-items/ai1",
      TEST_USER_ID,
    );
    expect(success).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns false on ApiError", async () => {
    mockDelete.mockRejectedValueOnce(new ApiError(403, "Forbidden", {}));

    const { useDeleteActionItem } =
      await import("../hooks/useDeleteActionItem");
    const { result } = renderHook(() => useDeleteActionItem("r1"));

    let success: boolean | undefined;
    await act(async () => {
      success = await result.current.deleteActionItem("ai1");
    });

    expect(success).toBe(false);
    expect(result.current.error).toBe(
      "アクションアイテムの削除に失敗しました (403)",
    );
  });

  it("sets generic error on non-ApiError", async () => {
    mockDelete.mockRejectedValueOnce(new Error("network"));

    const { useDeleteActionItem } =
      await import("../hooks/useDeleteActionItem");
    const { result } = renderHook(() => useDeleteActionItem("r1"));

    await act(async () => {
      await result.current.deleteActionItem("ai1");
    });

    expect(result.current.error).toBe("アクションアイテムの削除に失敗しました");
  });
});
