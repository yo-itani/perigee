import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { RecordViewerPage } from "../pages/RecordViewerPage";
import type { RecordDetail, RecordComment, RecordActionItem } from "../types";

// -- Mock data ----------------------------------------------------------------

const mockActionItems: RecordActionItem[] = [
  {
    action_item_id: "ai1",
    title: "資格取得の勉強計画を作成する",
    is_completed: false,
    counterpart_id: "cp-user-id-000001",
    created_at: "2026-04-01T10:00:00Z",
  },
  {
    action_item_id: "ai2",
    title: "進捗共有メールを送る",
    is_completed: true,
    counterpart_id: "cp-user-id-000001",
    created_at: "2026-04-01T10:00:00Z",
  },
];

const mockRecord: RecordDetail = {
  record_id: "r1",
  organizer_id: "00000000-0000-0000-0000-000000000001", // Same as dev user
  counterpart_id: "cp-user-id-000001",
  schedule_id: "s1",
  memo: "来季目標について：現在の達成率60%",
  status: "published",
  confirmed_agenda_ids: ["agenda-1", "agenda-2"],
  action_items: mockActionItems,
  conducted_at: "2026-04-03T10:00:00Z",
  created_at: "2026-03-20T10:00:00Z",
  updated_at: "2026-03-20T10:00:00Z",
};

const mockComments: RecordComment[] = [
  {
    comment_id: "c1",
    author_id: "cp-user-id-000001",
    body: "ありがとうございます。来季の目標については、引き続き取り組みます！",
    created_at: "2026-04-04T10:00:00Z",
  },
];

const mockViewerIds = ["cp-user-id-000001", "viewer-user-id-001"];

// -- Mock hooks ---------------------------------------------------------------

let recordDetailReturn = {
  record: mockRecord as RecordDetail | null,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

let recordCommentsReturn = {
  comments: mockComments,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

let recordViewersReturn = {
  viewerIds: mockViewerIds,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

const mockAddComment = vi.fn().mockResolvedValue({ comment_id: "c-new" });
let addRecordCommentReturn = {
  addComment: mockAddComment,
  isSubmitting: false,
  error: null as string | null,
};

const mockCompleteItem = vi.fn().mockResolvedValue({ action_item_id: "ai1" });
let completeActionItemReturn = {
  completeItem: mockCompleteItem,
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

vi.mock("../hooks/useRecordDetail", () => ({
  useRecordDetail: () => recordDetailReturn,
}));

vi.mock("../hooks/useRecordComments", () => ({
  useRecordComments: () => recordCommentsReturn,
}));

vi.mock("../hooks/useRecordViewers", () => ({
  useRecordViewers: () => recordViewersReturn,
}));

vi.mock("../hooks/useAddRecordComment", () => ({
  useAddRecordComment: () => addRecordCommentReturn,
}));

vi.mock("../hooks/useCompleteActionItem", () => ({
  useCompleteActionItem: () => completeActionItemReturn,
}));

// -- Helpers ------------------------------------------------------------------

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/records/r1"]}>
      <Routes>
        <Route path="records/:recordId" element={<RecordViewerPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("RecordViewerPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    recordDetailReturn = {
      record: mockRecord,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    recordCommentsReturn = {
      comments: mockComments,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    recordViewersReturn = {
      viewerIds: mockViewerIds,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    addRecordCommentReturn = {
      addComment: mockAddComment,
      isSubmitting: false,
      error: null,
    };
    completeActionItemReturn = {
      completeItem: mockCompleteItem,
      isSubmitting: false,
      error: null,
    };
  });

  // -- Normal data display --------------------------------------------------

  it("renders the record status", () => {
    renderPage();
    expect(screen.getByText("公開済み")).toBeInTheDocument();
  });

  it("renders the basic info card", () => {
    renderPage();
    expect(screen.getByText("基本情報")).toBeInTheDocument();
    expect(screen.getByText("published")).toBeInTheDocument();
  });

  it("renders the agenda section", () => {
    renderPage();
    expect(screen.getByText("アジェンダ")).toBeInTheDocument();
  });

  it("renders the memo", () => {
    renderPage();
    expect(screen.getByText("記録（メモ）")).toBeInTheDocument();
    expect(
      screen.getByText("来季目標について：現在の達成率60%"),
    ).toBeInTheDocument();
  });

  it("renders action items", () => {
    renderPage();
    expect(screen.getByText("アクションアイテム")).toBeInTheDocument();
    expect(
      screen.getByText("資格取得の勉強計画を作成する"),
    ).toBeInTheDocument();
    expect(screen.getByText("進捗共有メールを送る")).toBeInTheDocument();
  });

  it("renders incomplete action item with complete button", () => {
    renderPage();
    const completeButtons = screen.getAllByRole("button", { name: "完了" });
    // Only 1 incomplete item should have a complete button
    expect(completeButtons).toHaveLength(1);
  });

  it("renders viewers section", () => {
    renderPage();
    expect(screen.getByText("公開先")).toBeInTheDocument();
  });

  it("renders comments", () => {
    renderPage();
    expect(screen.getByText("コメント")).toBeInTheDocument();
    expect(
      screen.getByText(
        "ありがとうございます。来季の目標については、引き続き取り組みます！",
      ),
    ).toBeInTheDocument();
  });

  // -- Role-based display ---------------------------------------------------

  it("shows edit button for organizer role", () => {
    renderPage();
    expect(
      screen.getByRole("button", { name: "編集する" }),
    ).toBeInTheDocument();
  });

  it("hides edit button for counterpart role", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: {
        ...mockRecord,
        organizer_id: "other-user",
        counterpart_id: "00000000-0000-0000-0000-000000000001",
      },
    };
    renderPage();
    expect(
      screen.queryByRole("button", { name: "編集する" }),
    ).not.toBeInTheDocument();
  });

  it("hides edit button for viewer role", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: {
        ...mockRecord,
        organizer_id: "other-user",
        counterpart_id: "another-user",
      },
    };
    renderPage();
    expect(
      screen.queryByRole("button", { name: "編集する" }),
    ).not.toBeInTheDocument();
  });

  // -- Loading state --------------------------------------------------------

  it("shows loading skeletons when data is loading", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: null,
      isLoading: true,
    };
    recordCommentsReturn = {
      ...recordCommentsReturn,
      comments: [],
      isLoading: true,
    };
    recordViewersReturn = {
      ...recordViewersReturn,
      viewerIds: [],
      isLoading: true,
    };

    const { container } = renderPage();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // -- Error state ----------------------------------------------------------

  it("shows error messages when API calls fail", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: null,
      error: "記録の取得に失敗しました",
    };
    recordCommentsReturn = {
      ...recordCommentsReturn,
      comments: [],
      error: "コメントの取得に失敗しました",
    };

    renderPage();
    expect(screen.getByText("記録の取得に失敗しました")).toBeInTheDocument();
    expect(
      screen.getByText("コメントの取得に失敗しました"),
    ).toBeInTheDocument();
  });

  // -- Complete action item -------------------------------------------------

  it("calls completeItem when clicking complete button", async () => {
    const user = userEvent.setup();
    renderPage();

    const completeButton = screen.getByRole("button", { name: "完了" });
    await user.click(completeButton);

    expect(mockCompleteItem).toHaveBeenCalledWith("ai1");
  });

  it("shows complete error message", () => {
    completeActionItemReturn = {
      ...completeActionItemReturn,
      error: "アクションアイテムの完了に失敗しました (400)",
    };

    renderPage();
    expect(
      screen.getByText("アクションアイテムの完了に失敗しました (400)"),
    ).toBeInTheDocument();
  });

  // -- Add comment ----------------------------------------------------------

  it("calls addComment when submitting a comment", async () => {
    const user = userEvent.setup();
    renderPage();

    const textarea = screen.getByPlaceholderText("コメントを追加...");
    await user.type(textarea, "新しいコメント");
    const submitButton = screen.getByRole("button", { name: "送信" });
    await user.click(submitButton);

    expect(mockAddComment).toHaveBeenCalledWith("新しいコメント");
  });

  it("clears comment input on successful submission", async () => {
    mockAddComment.mockResolvedValueOnce({ comment_id: "c-new" });
    const user = userEvent.setup();
    renderPage();

    const textarea = screen.getByPlaceholderText("コメントを追加...");
    await user.type(textarea, "成功コメント");
    const submitButton = screen.getByRole("button", { name: "送信" });
    await user.click(submitButton);

    await waitFor(() => {
      expect(textarea).toHaveValue("");
    });
  });

  it("does not clear comment input when addComment fails", async () => {
    mockAddComment.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const textarea = screen.getByPlaceholderText("コメントを追加...");
    await user.type(textarea, "失敗コメント");
    const submitButton = screen.getByRole("button", { name: "送信" });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockAddComment).toHaveBeenCalled();
    });

    expect(textarea).toHaveValue("失敗コメント");
  });

  it("shows addComment error message", () => {
    addRecordCommentReturn = {
      ...addRecordCommentReturn,
      error: "コメントの追加に失敗しました (500)",
    };

    renderPage();
    expect(
      screen.getByText("コメントの追加に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  it("disables send button when comment is empty", () => {
    renderPage();
    const submitButton = screen.getByRole("button", { name: "送信" });
    expect(submitButton).toBeDisabled();
  });

  // -- Empty states ---------------------------------------------------------

  it("shows empty memo message when no memo", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: { ...mockRecord, memo: "" },
    };

    renderPage();
    expect(screen.getByText("メモはまだありません")).toBeInTheDocument();
  });

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

  // -- Viewer role display --------------------------------------------------

  it("shows only current user in viewer list for viewer role", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: {
        ...mockRecord,
        organizer_id: "other-user",
        counterpart_id: "another-user",
      },
    };
    recordViewersReturn = {
      ...recordViewersReturn,
      viewerIds: ["00000000-0000-0000-0000-000000000001", "another-viewer"],
    };

    renderPage();
    // Should show current user but not other viewers
    expect(
      screen.getByText("00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
    expect(screen.queryByText("another-viewer")).not.toBeInTheDocument();
  });

  // -- Navigation -----------------------------------------------------------

  it("navigates to recording page when clicking edit", async () => {
    const user = userEvent.setup();
    renderPage();

    const editButton = screen.getByRole("button", { name: "編集する" });
    await user.click(editButton);

    expect(mockNavigate).toHaveBeenCalledWith("/records/r1/recording");
  });
});
