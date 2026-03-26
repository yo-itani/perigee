import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { RecordingPage } from "../pages/RecordingPage";
import type { RecordDetail, RecordActionItem } from "../types";
import type { AgendaItem } from "@/features/preparation/types";

// -- Mock data ----------------------------------------------------------------

const mockActionItems: RecordActionItem[] = [
  {
    action_item_id: "ai1",
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
  memo: "テストメモ",
  status: "draft",
  confirmed_agenda_ids: ["a1"],
  action_items: mockActionItems,
  conducted_at: "2026-04-01T10:00:00Z",
  created_at: "2026-03-20T10:00:00Z",
  updated_at: "2026-03-20T10:00:00Z",
};

const mockAgendas: AgendaItem[] = [
  {
    agenda_id: "a1",
    topic: "前回のアクションアイテム確認",
    added_by: "org1",
    added_by_tag: "template",
    comments: [],
    created_at: "2026-03-20T10:00:00Z",
  },
  {
    agenda_id: "a2",
    topic: "業務状況の共有",
    added_by: "org1",
    added_by_tag: "template",
    comments: [],
    created_at: "2026-03-20T10:00:00Z",
  },
];

// -- Mock hooks ---------------------------------------------------------------

let recordDetailReturn = {
  record: mockRecord as RecordDetail | null,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

let scheduleAgendasReturn = {
  agendas: mockAgendas,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

const mockAddAgenda = vi.fn().mockResolvedValue({ agenda_id: "a3" });
let addAgendaReturn = {
  addAgenda: mockAddAgenda,
  isSubmitting: false,
  error: null as string | null,
};

const mockConfirmAgenda = vi
  .fn()
  .mockResolvedValue({ record_id: "r1", agenda_id: "a2" });
let confirmAgendaReturn = {
  confirmAgenda: mockConfirmAgenda,
  isSubmitting: false,
  error: null as string | null,
};

const mockAddActionItem = vi
  .fn()
  .mockResolvedValue({ action_item_id: "ai-new" });
let addActionItemReturn = {
  addActionItem: mockAddActionItem,
  isSubmitting: false,
  error: null as string | null,
};

const mockDeleteActionItem = vi.fn().mockResolvedValue(true);
let deleteActionItemReturn = {
  deleteActionItem: mockDeleteActionItem,
  isSubmitting: false,
  error: null as string | null,
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

vi.mock("@/features/preparation/hooks/useScheduleAgendas", () => ({
  useScheduleAgendas: () => scheduleAgendasReturn,
}));

vi.mock("@/features/preparation/hooks/useAddAgenda", () => ({
  useAddAgenda: () => addAgendaReturn,
}));

vi.mock("../hooks/useConfirmAgenda", () => ({
  useConfirmAgenda: () => confirmAgendaReturn,
}));

vi.mock("../hooks/useAddActionItem", () => ({
  useAddActionItem: () => addActionItemReturn,
}));

vi.mock("../hooks/useDeleteActionItem", () => ({
  useDeleteActionItem: () => deleteActionItemReturn,
}));

vi.mock("@/hooks/useUpdateMemo", () => ({
  useUpdateMemo: () => updateMemoReturn,
}));

vi.mock("@/hooks/useSaveDraft", () => ({
  useSaveDraft: () => saveDraftReturn,
}));

// -- Helpers ------------------------------------------------------------------

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/records/r1/recording"]}>
      <Routes>
        <Route path="records/:recordId/recording" element={<RecordingPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("RecordingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    recordDetailReturn = {
      record: mockRecord,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    scheduleAgendasReturn = {
      agendas: mockAgendas,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    addAgendaReturn = {
      addAgenda: mockAddAgenda,
      isSubmitting: false,
      error: null,
    };
    confirmAgendaReturn = {
      confirmAgenda: mockConfirmAgenda,
      isSubmitting: false,
      error: null,
    };
    addActionItemReturn = {
      addActionItem: mockAddActionItem,
      isSubmitting: false,
      error: null,
    };
    deleteActionItemReturn = {
      deleteActionItem: mockDeleteActionItem,
      isSubmitting: false,
      error: null,
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
  });

  // -- Normal data display --------------------------------------------------

  it("renders the page title", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: /1on1 記録/ }),
    ).toBeInTheDocument();
  });

  it("renders the status bar", () => {
    renderPage();
    expect(screen.getByText("実施中")).toBeInTheDocument();
  });

  it("renders agenda items with checkboxes", () => {
    renderPage();
    expect(screen.getByText("アジェンダ")).toBeInTheDocument();
    expect(
      screen.getByText("前回のアクションアイテム確認"),
    ).toBeInTheDocument();
    expect(screen.getByText("業務状況の共有")).toBeInTheDocument();
  });

  it("renders confirmed agenda with check mark", () => {
    renderPage();
    // a1 is confirmed
    const checkbox = screen.getByRole("checkbox", {
      name: "前回のアクションアイテム確認を確認",
    });
    expect(checkbox).toHaveAttribute("aria-checked", "true");
  });

  it("renders unconfirmed agenda without check mark", () => {
    renderPage();
    const checkbox = screen.getByRole("checkbox", {
      name: "業務状況の共有を確認",
    });
    expect(checkbox).toHaveAttribute("aria-checked", "false");
  });

  it("renders memo editor with initial memo", () => {
    renderPage();
    expect(screen.getByText("メモ")).toBeInTheDocument();
    const textarea = screen.getByRole("textbox", { name: "メモ" });
    expect(textarea).toHaveValue("テストメモ");
  });

  it("renders action items", () => {
    renderPage();
    expect(screen.getByText("アクションアイテム")).toBeInTheDocument();
    expect(screen.getByText("進捗共有メールを送る")).toBeInTheDocument();
  });

  it("renders the complete button", () => {
    renderPage();
    const buttons = screen.getAllByRole("button", {
      name: "完了として保存",
    });
    expect(buttons.length).toBeGreaterThan(0);
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

  // -- Confirm agenda -------------------------------------------------------

  it("calls confirmAgenda when clicking unconfirmed agenda checkbox", async () => {
    const user = userEvent.setup();
    renderPage();

    const checkbox = screen.getByRole("checkbox", {
      name: "業務状況の共有を確認",
    });
    await user.click(checkbox);

    expect(mockConfirmAgenda).toHaveBeenCalledWith("a2");
  });

  // -- Add agenda -----------------------------------------------------------

  it("calls addAgenda when submitting a new agenda", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByPlaceholderText("話題が増えたら追加...");
    await user.type(input, "新しいアジェンダ");
    const addButton = screen.getAllByRole("button", { name: "追加" })[0];
    await user.click(addButton);

    expect(mockAddAgenda).toHaveBeenCalledWith("新しいアジェンダ");
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

  // -- Add action item ------------------------------------------------------

  it("calls addActionItem when submitting a new action item", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByPlaceholderText("アクションアイテムを追加...");
    await user.type(input, "新しいアクション");
    // Get the add button in the action item section (last "追加" button)
    const addButtons = screen.getAllByRole("button", { name: "追加" });
    await user.click(addButtons[addButtons.length - 1]);

    // handleAddActionItem receives (title, dueDate?) but forwards only title to hook
    expect(mockAddActionItem).toHaveBeenCalledWith("新しいアクション");
  });

  // -- Delete action item ---------------------------------------------------

  it("calls deleteActionItem when clicking delete button", async () => {
    const user = userEvent.setup();
    renderPage();

    const deleteButton = screen.getByRole("button", {
      name: "進捗共有メールを送るを削除",
    });
    await user.click(deleteButton);

    expect(mockDeleteActionItem).toHaveBeenCalledWith("ai1");
  });

  // -- Save and complete ----------------------------------------------------

  it("navigates to publish page when clicking complete button", async () => {
    const user = userEvent.setup();
    renderPage();

    const completeButtons = screen.getAllByRole("button", {
      name: "完了として保存",
    });
    await user.click(completeButtons[0]);

    await waitFor(() => {
      expect(mockUpdateMemo).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockSaveDraft).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/records/r1/publish");
    });
  });

  it("does not call saveDraft when updateMemo fails", async () => {
    mockUpdateMemo.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const completeButtons = screen.getAllByRole("button", {
      name: "完了として保存",
    });
    await user.click(completeButtons[0]);

    await waitFor(() => {
      expect(mockUpdateMemo).toHaveBeenCalled();
    });

    expect(mockSaveDraft).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // -- Input preserved on error ---------------------------------------------

  it("does not clear agenda input when addAgenda fails", async () => {
    mockAddAgenda.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByPlaceholderText("話題が増えたら追加...");
    await user.type(input, "失敗するアジェンダ");
    const addButton = screen.getAllByRole("button", { name: "追加" })[0];
    await user.click(addButton);

    await waitFor(() => {
      expect(mockAddAgenda).toHaveBeenCalledWith("失敗するアジェンダ");
    });

    expect(input).toHaveValue("失敗するアジェンダ");
  });

  it("does not clear action item input when addActionItem fails", async () => {
    mockAddActionItem.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByPlaceholderText("アクションアイテムを追加...");
    await user.type(input, "失敗するアクション");
    const addButtons = screen.getAllByRole("button", { name: "追加" });
    await user.click(addButtons[addButtons.length - 1]);

    await waitFor(() => {
      expect(mockAddActionItem).toHaveBeenCalledWith("失敗するアクション");
    });

    expect(input).toHaveValue("失敗するアクション");
  });

  // -- Mutation error display -----------------------------------------------

  it("shows confirmAgenda error message", () => {
    confirmAgendaReturn = {
      ...confirmAgendaReturn,
      error: "アジェンダの確認に失敗しました (500)",
    };

    renderPage();
    expect(
      screen.getByText("アジェンダの確認に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  it("shows addActionItem error message", () => {
    addActionItemReturn = {
      ...addActionItemReturn,
      error: "アクションアイテムの追加に失敗しました (500)",
    };

    renderPage();
    expect(
      screen.getByText("アクションアイテムの追加に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  it("shows deleteActionItem error message", () => {
    deleteActionItemReturn = {
      ...deleteActionItemReturn,
      error: "アクションアイテムの削除に失敗しました (500)",
    };

    renderPage();
    expect(
      screen.getByText("アクションアイテムの削除に失敗しました (500)"),
    ).toBeInTheDocument();
  });

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

  // -- Empty state ----------------------------------------------------------

  it("shows empty message when no action items", () => {
    recordDetailReturn = {
      ...recordDetailReturn,
      record: { ...mockRecord, action_items: [] },
    };

    renderPage();
    expect(
      screen.getByText("アクションアイテムはまだありません"),
    ).toBeInTheDocument();
  });

  it("shows empty message when no agendas", () => {
    scheduleAgendasReturn = {
      ...scheduleAgendasReturn,
      agendas: [],
    };

    renderPage();
    expect(screen.getByText("アジェンダはまだありません")).toBeInTheDocument();
  });
});
