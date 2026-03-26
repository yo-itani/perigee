import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { PublishingPage } from "../pages/PublishingPage";
import type {
  RecordDetail,
  RecordActionItem,
} from "@/features/recording/types";

// -- Mock data ----------------------------------------------------------------

const mockActionItems: RecordActionItem[] = [
  {
    action_item_id: "ai1",
    title: "資格取得の勉強計画を作成する",
    is_completed: false,
    counterpart_id: "cp1",
    created_at: "2026-03-20T10:00:00Z",
    due_date: "2026-04-10T00:00:00Z",
  },
  {
    action_item_id: "ai2",
    title: "進捗共有メールを送る",
    is_completed: false,
    counterpart_id: "cp1",
    created_at: "2026-03-20T10:00:00Z",
  },
];

const mockRecord: RecordDetail = {
  record_id: "r1",
  organizer_id: "org1",
  counterpart_id: "cp1",
  schedule_id: "s1",
  memo: "テストメモの内容",
  status: "draft",
  confirmed_agenda_ids: ["a1"],
  action_items: mockActionItems,
  conducted_at: "2026-04-03T10:00:00Z",
  created_at: "2026-03-20T10:00:00Z",
  updated_at: "2026-03-20T10:00:00Z",
};

const mockSuggestedViewerIds = ["cp1", "viewer1"];

// -- Mock hooks ---------------------------------------------------------------

let recordDetailReturn = {
  record: mockRecord as RecordDetail | null,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

let suggestedViewersReturn = {
  suggestedViewerIds: mockSuggestedViewerIds,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

const mockUpdateMemo = vi.fn().mockResolvedValue({ record_id: "r1" });
let updateMemoReturn = {
  updateMemo: mockUpdateMemo,
  isSubmitting: false,
  error: null as string | null,
};

const mockSaveDraft = vi.fn().mockResolvedValue({ record_id: "r1" });
let saveDraftReturn = {
  saveDraft: mockSaveDraft,
  isSubmitting: false,
  error: null as string | null,
};

const mockSetViewers = vi.fn().mockResolvedValue({ record_id: "r1" });
let setViewersReturn = {
  setViewers: mockSetViewers,
  isSubmitting: false,
  error: null as string | null,
};

const mockPublishRecord = vi.fn().mockResolvedValue({ record_id: "r1" });
let publishRecordReturn = {
  publishRecord: mockPublishRecord,
  isSubmitting: false,
  error: null as string | null,
};

const mockNavigate = vi.fn();

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    userId: "00000000-0000-0000-0000-000000000001",
    name: "Dev User",
  }),
}));

vi.mock("@/features/recording/hooks/useRecordDetail", () => ({
  useRecordDetail: () => recordDetailReturn,
}));

vi.mock("../hooks/useSuggestedViewers", () => ({
  useSuggestedViewers: () => suggestedViewersReturn,
}));

vi.mock("@/hooks/useUpdateMemo", () => ({
  useUpdateMemo: () => updateMemoReturn,
}));

vi.mock("@/hooks/useSaveDraft", () => ({
  useSaveDraft: () => saveDraftReturn,
}));

vi.mock("../hooks/useSetViewers", () => ({
  useSetViewers: () => setViewersReturn,
}));

vi.mock("../hooks/usePublishRecord", () => ({
  usePublishRecord: () => publishRecordReturn,
}));

// -- Helpers ------------------------------------------------------------------

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/records/r1/publish"]}>
      <Routes>
        <Route path="records/:recordId/publish" element={<PublishingPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("PublishingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    recordDetailReturn = {
      record: mockRecord,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    suggestedViewersReturn = {
      suggestedViewerIds: mockSuggestedViewerIds,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    updateMemoReturn = {
      updateMemo: mockUpdateMemo,
      isSubmitting: false,
      error: null,
    };
    saveDraftReturn = {
      saveDraft: mockSaveDraft,
      isSubmitting: false,
      error: null,
    };
    setViewersReturn = {
      setViewers: mockSetViewers,
      isSubmitting: false,
      error: null,
    };
    publishRecordReturn = {
      publishRecord: mockPublishRecord,
      isSubmitting: false,
      error: null,
    };
  });

  // -- Normal data display --------------------------------------------------

  it("renders the page title", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: /公開フロー/ }),
    ).toBeInTheDocument();
  });

  it("renders status badge", () => {
    renderPage();
    expect(screen.getByText("下書き")).toBeInTheDocument();
  });

  it("renders the status bar", () => {
    renderPage();
    expect(screen.getByText("1on1 完了・記録を編集中")).toBeInTheDocument();
  });

  it("renders memo editor with initial memo", () => {
    renderPage();
    expect(screen.getByText("記録（メモ）")).toBeInTheDocument();
    const textarea = screen.getByRole("textbox", { name: "メモ" });
    expect(textarea).toHaveValue("テストメモの内容");
  });

  it("renders action items in read-only summary", () => {
    renderPage();
    expect(screen.getByText("アクションアイテム")).toBeInTheDocument();
    expect(
      screen.getByText("資格取得の勉強計画を作成する"),
    ).toBeInTheDocument();
    expect(screen.getByText("進捗共有メールを送る")).toBeInTheDocument();
  });

  it("renders action item due date when present", () => {
    renderPage();
    expect(screen.getByText("期限：2026/04/10")).toBeInTheDocument();
  });

  it("renders the save draft button", () => {
    renderPage();
    expect(
      screen.getByRole("button", { name: "下書き保存" }),
    ).toBeInTheDocument();
  });

  it("renders the publish settings button", () => {
    renderPage();
    expect(
      screen.getByRole("button", { name: "公開設定へ" }),
    ).toBeInTheDocument();
  });

  // -- Loading state --------------------------------------------------------

  it("shows loading skeleton when record is loading", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: null,
      isLoading: true,
    };

    const { container } = renderPage();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows loading skeleton when suggested viewers are loading", () => {
    suggestedViewersReturn = {
      ...suggestedViewersReturn,
      isLoading: true,
    };

    const { container } = renderPage();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // -- Error state ----------------------------------------------------------

  it("shows error message when record fetch fails", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: null,
      error: "記録の取得に失敗しました",
    };

    renderPage();
    expect(screen.getByText("記録の取得に失敗しました")).toBeInTheDocument();
  });

  it("shows error message when suggested viewers fetch fails", () => {
    suggestedViewersReturn = {
      ...suggestedViewersReturn,
      error: "公開先サジェストの取得に失敗しました (500)",
    };

    renderPage();
    expect(
      screen.getByText("公開先サジェストの取得に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  // -- Memo update ----------------------------------------------------------

  it("updates memo text on input change", async () => {
    const user = userEvent.setup();
    renderPage();

    const textarea = screen.getByRole("textbox", { name: "メモ" });
    await user.clear(textarea);
    await user.type(textarea, "新しいメモ");

    expect(textarea).toHaveValue("新しいメモ");
  });

  // -- Save draft -----------------------------------------------------------

  it("calls updateMemo and saveDraft when clicking save draft button", async () => {
    const user = userEvent.setup();
    renderPage();

    const saveButton = screen.getByRole("button", { name: "下書き保存" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateMemo).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockSaveDraft).toHaveBeenCalled();
    });
  });

  it("does not call saveDraft when updateMemo fails during save draft", async () => {
    mockUpdateMemo.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const saveButton = screen.getByRole("button", { name: "下書き保存" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateMemo).toHaveBeenCalled();
    });

    expect(mockSaveDraft).not.toHaveBeenCalled();
  });

  // -- Open modal -----------------------------------------------------------

  it("opens the viewer select modal when clicking publish settings button", async () => {
    const user = userEvent.setup();
    renderPage();

    const publishButton = screen.getByRole("button", { name: "公開設定へ" });
    await user.click(publishButton);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("公開設定")).toBeInTheDocument();
  });

  // -- Publish flow ---------------------------------------------------------

  it("calls updateMemo, setViewers, and publishRecord when publishing", async () => {
    const user = userEvent.setup();
    renderPage();

    // Open modal
    const publishButton = screen.getByRole("button", { name: "公開設定へ" });
    await user.click(publishButton);

    // Click publish (default timing is "now")
    const confirmButton = screen.getByRole("button", { name: "公開する" });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockUpdateMemo).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockSetViewers).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockPublishRecord).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/records/r1");
    });
  });

  it("does not call setViewers when updateMemo fails during publish", async () => {
    mockUpdateMemo.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const publishButton = screen.getByRole("button", { name: "公開設定へ" });
    await user.click(publishButton);

    const confirmButton = screen.getByRole("button", { name: "公開する" });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockUpdateMemo).toHaveBeenCalled();
    });

    expect(mockSetViewers).not.toHaveBeenCalled();
    expect(mockPublishRecord).not.toHaveBeenCalled();
  });

  it("does not call publishRecord when setViewers fails", async () => {
    mockSetViewers.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const publishButton = screen.getByRole("button", { name: "公開設定へ" });
    await user.click(publishButton);

    const confirmButton = screen.getByRole("button", { name: "公開する" });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockSetViewers).toHaveBeenCalled();
    });

    expect(mockPublishRecord).not.toHaveBeenCalled();
  });

  // -- Draft from modal -----------------------------------------------------

  it("saves draft from modal when selecting draft timing", async () => {
    const user = userEvent.setup();
    renderPage();

    const publishButton = screen.getByRole("button", { name: "公開設定へ" });
    await user.click(publishButton);

    // Select draft timing
    const draftRadio = screen.getByRole("radio", {
      name: /下書きとして保存/,
    });
    await user.click(draftRadio);

    // There are two "下書き保存" buttons (footer + modal), take the modal one (last)
    const draftButtons = screen.getAllByRole("button", { name: "下書き保存" });
    await user.click(draftButtons[draftButtons.length - 1]);

    await waitFor(() => {
      expect(mockUpdateMemo).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockSetViewers).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockSaveDraft).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/records/drafts");
    });
  });

  // -- Close modal ----------------------------------------------------------

  it("closes modal when clicking cancel", async () => {
    const user = userEvent.setup();
    renderPage();

    const publishButton = screen.getByRole("button", { name: "公開設定へ" });
    await user.click(publishButton);

    expect(screen.getByRole("dialog")).toBeInTheDocument();

    const cancelButton = screen.getByRole("button", { name: "キャンセル" });
    await user.click(cancelButton);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  // -- Mutation error display -----------------------------------------------

  it("shows memo save error message", () => {
    updateMemoReturn = {
      ...updateMemoReturn,
      error: "メモの保存に失敗しました (500)",
    };

    renderPage();
    expect(
      screen.getByText("メモの保存に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  it("shows saveDraft error message", () => {
    saveDraftReturn = {
      ...saveDraftReturn,
      error: "下書き保存に失敗しました (500)",
    };

    renderPage();
    expect(
      screen.getByText("下書き保存に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  it("shows setViewers error message", () => {
    setViewersReturn = {
      ...setViewersReturn,
      error: "公開先の設定に失敗しました (400)",
    };

    renderPage();
    expect(
      screen.getByText("公開先の設定に失敗しました (400)"),
    ).toBeInTheDocument();
  });

  // -- Empty action items ---------------------------------------------------

  it("shows empty message when no action items", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: { ...mockRecord, action_items: [] },
    };

    renderPage();
    expect(
      screen.getByText("アクションアイテムはありません"),
    ).toBeInTheDocument();
  });

  // -- Double-submit prevention on save draft --------------------------------

  it("does not double-fire updateMemo when blur and save draft overlap", async () => {
    mockUpdateMemo.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ record_id: "r1" }), 50),
        ),
    );
    const user = userEvent.setup();
    renderPage();

    const textarea = screen.getByRole("textbox", { name: "メモ" });
    await user.type(textarea, "追記");

    const saveButton = screen.getByRole("button", { name: "下書き保存" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockSaveDraft).toHaveBeenCalled();
    });

    // updateMemo should be called exactly once (from handleSaveDraft),
    // blur is skipped because dirty check sees memo was already marked as saved
    expect(mockUpdateMemo).toHaveBeenCalledTimes(1);
  });
});
