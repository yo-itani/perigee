import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
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

// -- useScheduleDetail --------------------------------------------------------

describe("useScheduleDetail", () => {
  it("fetches schedule detail on mount and returns data", async () => {
    const mockSchedule = {
      schedule_id: "s1",
      organizer_id: "org1",
      counterpart_id: "cp1",
      title: "Test 1on1",
      scheduled_at: "2026-04-01T10:00:00Z",
      status: "confirmed",
      schedule_group_id: null,
      created_at: "2026-03-20T10:00:00Z",
      updated_at: "2026-03-20T10:00:00Z",
    };
    mockGet.mockResolvedValueOnce(mockSchedule);

    const { useScheduleDetail } = await import("../hooks/useScheduleDetail");
    const { result } = renderHook(() => useScheduleDetail("s1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith("/schedules/s1");
    expect(result.current.schedule).toEqual(mockSchedule);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(404, "Not Found", {}));

    const { useScheduleDetail } = await import("../hooks/useScheduleDetail");
    const { result } = renderHook(() => useScheduleDetail("s1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.schedule).toBeNull();
    expect(result.current.error).toBe("スケジュールの取得に失敗しました (404)");
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { useScheduleDetail } = await import("../hooks/useScheduleDetail");
    const { result } = renderHook(() => useScheduleDetail("s1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("スケジュールの取得に失敗しました");
  });
});

// -- useScheduleAgendas -------------------------------------------------------

describe("useScheduleAgendas", () => {
  it("fetches agendas on mount and returns data", async () => {
    const mockAgendas = {
      agendas: [
        {
          agenda_id: "a1",
          topic: "Topic 1",
          added_by: "org1",
          added_by_tag: "organizer",
          comments: [],
          created_at: "2026-03-20T10:00:00Z",
        },
      ],
    };
    mockGet.mockResolvedValueOnce(mockAgendas);

    const { useScheduleAgendas } = await import("../hooks/useScheduleAgendas");
    const { result } = renderHook(() => useScheduleAgendas("s1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith("/schedules/s1/agendas");
    expect(result.current.agendas).toEqual(mockAgendas.agendas);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(500, "Server Error", {}));

    const { useScheduleAgendas } = await import("../hooks/useScheduleAgendas");
    const { result } = renderHook(() => useScheduleAgendas("s1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.agendas).toEqual([]);
    expect(result.current.error).toBe("アジェンダの取得に失敗しました (500)");
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { useScheduleAgendas } = await import("../hooks/useScheduleAgendas");
    const { result } = renderHook(() => useScheduleAgendas("s1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("アジェンダの取得に失敗しました");
  });
});

// -- useAddAgenda -------------------------------------------------------------

describe("useAddAgenda", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { agenda_id: "a-new" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { useAddAgenda } = await import("../hooks/useAddAgenda");
    const { result } = renderHook(() => useAddAgenda("s1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.addAgenda("New topic");
    });

    expect(mockPost).toHaveBeenCalledWith("/schedules/s1/agendas", {
      topic: "New topic",
    });
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useAddAgenda } = await import("../hooks/useAddAgenda");
    const { result } = renderHook(() => useAddAgenda("s1"));

    let response: unknown;
    await act(async () => {
      response = await result.current.addAgenda("Bad topic");
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("アジェンダの追加に失敗しました (400)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { useAddAgenda } = await import("../hooks/useAddAgenda");
    const { result } = renderHook(() => useAddAgenda("s1"));

    await act(async () => {
      await result.current.addAgenda("topic");
    });

    expect(result.current.error).toBe("アジェンダの追加に失敗しました");
  });
});

// -- useDeleteAgenda ----------------------------------------------------------

describe("useDeleteAgenda", () => {
  it("calls API and returns true on success", async () => {
    mockDelete.mockResolvedValueOnce(undefined);

    const { useDeleteAgenda } = await import("../hooks/useDeleteAgenda");
    const { result } = renderHook(() => useDeleteAgenda("s1"));

    let success: boolean | undefined;
    await act(async () => {
      success = await result.current.deleteAgenda("a1");
    });

    expect(mockDelete).toHaveBeenCalledWith("/schedules/s1/agendas/a1");
    expect(success).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns false on ApiError", async () => {
    mockDelete.mockRejectedValueOnce(new ApiError(403, "Forbidden", {}));

    const { useDeleteAgenda } = await import("../hooks/useDeleteAgenda");
    const { result } = renderHook(() => useDeleteAgenda("s1"));

    let success: boolean | undefined;
    await act(async () => {
      success = await result.current.deleteAgenda("a1");
    });

    expect(success).toBe(false);
    expect(result.current.error).toBe("アジェンダの削除に失敗しました (403)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockDelete.mockRejectedValueOnce(new Error("network"));

    const { useDeleteAgenda } = await import("../hooks/useDeleteAgenda");
    const { result } = renderHook(() => useDeleteAgenda("s1"));

    await act(async () => {
      await result.current.deleteAgenda("a1");
    });

    expect(result.current.error).toBe("アジェンダの削除に失敗しました");
  });
});

// -- useAddAgendaComment ------------------------------------------------------

describe("useAddAgendaComment", () => {
  it("calls API and returns response on success", async () => {
    const mockResponse = { comment_id: "c-new" };
    mockPost.mockResolvedValueOnce(mockResponse);

    const { useAddAgendaComment } =
      await import("../hooks/useAddAgendaComment");
    const { result } = renderHook(() => useAddAgendaComment());

    let response: unknown;
    await act(async () => {
      response = await result.current.addComment("a1", "Great point");
    });

    expect(mockPost).toHaveBeenCalledWith("/agendas/a1/comments", {
      body: "Great point",
    });
    expect(response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on ApiError", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(422, "Unprocessable", {}));

    const { useAddAgendaComment } =
      await import("../hooks/useAddAgendaComment");
    const { result } = renderHook(() => useAddAgendaComment());

    let response: unknown;
    await act(async () => {
      response = await result.current.addComment("a1", "");
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("コメントの追加に失敗しました (422)");
  });

  it("sets generic error on non-ApiError", async () => {
    mockPost.mockRejectedValueOnce(new Error("network"));

    const { useAddAgendaComment } =
      await import("../hooks/useAddAgendaComment");
    const { result } = renderHook(() => useAddAgendaComment());

    await act(async () => {
      await result.current.addComment("a1", "body");
    });

    expect(result.current.error).toBe("コメントの追加に失敗しました");
  });
});

// -- usePendingActionItems ----------------------------------------------------

describe("usePendingActionItems", () => {
  it("fetches pending items on mount and returns data", async () => {
    const mockItems = {
      items: [
        {
          action_item_id: "ai1",
          content: "Follow up on report",
          created_at: "2026-03-20T10:00:00Z",
          record_id: "r1",
          organizer_id: "org1",
          conducted_at: "2026-03-20T10:00:00Z",
        },
      ],
    };
    mockGet.mockResolvedValueOnce(mockItems);

    const { usePendingActionItems } =
      await import("../hooks/usePendingActionItems");
    const { result } = renderHook(() => usePendingActionItems("cp1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith("/action-items/pending/cp1");
    expect(result.current.items).toEqual(mockItems.items);
    expect(result.current.error).toBeNull();
  });

  it("returns empty items when counterpartId is null", async () => {
    const { usePendingActionItems } =
      await import("../hooks/usePendingActionItems");
    const { result } = renderHook(() => usePendingActionItems(null));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).not.toHaveBeenCalled();
    expect(result.current.items).toEqual([]);
  });

  it("sets error when API call fails with ApiError", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(500, "Server Error", {}));

    const { usePendingActionItems } =
      await import("../hooks/usePendingActionItems");
    const { result } = renderHook(() => usePendingActionItems("cp1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.items).toEqual([]);
    expect(result.current.error).toBe(
      "アクションアイテムの取得に失敗しました (500)",
    );
  });

  it("sets generic error when a non-ApiError is thrown", async () => {
    mockGet.mockRejectedValueOnce(new Error("network failure"));

    const { usePendingActionItems } =
      await import("../hooks/usePendingActionItems");
    const { result } = renderHook(() => usePendingActionItems("cp1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("アクションアイテムの取得に失敗しました");
  });
});
