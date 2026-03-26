import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { PreparationPage } from "../pages/PreparationPage";
import type { ScheduleDetail, AgendaItem, PendingActionItem } from "../types";

// -- Mock data ----------------------------------------------------------------

const mockSchedule: ScheduleDetail = {
  schedule_id: "s1",
  organizer_id: "org-user-id-00001",
  counterpart_id: "cp-user-id-000001",
  title: "Weekly 1on1 -- Tanaka",
  scheduled_at: new Date(Date.now() + 3 * 86400000).toISOString(),
  status: "confirmed",
  schedule_group_id: null,
  created_at: "2026-03-20T10:00:00Z",
  updated_at: "2026-03-20T10:00:00Z",
};

const mockAgendas: AgendaItem[] = [
  {
    agenda_id: "a1",
    topic: "前回のアクションアイテム確認",
    added_by: "org-user-id-00001",
    added_by_tag: "template",
    comments: [],
    created_at: "2026-03-20T10:00:00Z",
  },
  {
    agenda_id: "a2",
    topic: "来季の目標設定",
    added_by: "cp-user-id-000001",
    added_by_tag: "counterpart",
    comments: [
      {
        comment_id: "c1",
        author_id: "cp-user-id-000001",
        body: "現在の達成率は60%ほどです。",
        created_at: "2026-03-31T10:00:00Z",
      },
    ],
    created_at: "2026-03-20T10:00:00Z",
  },
];

const mockPendingItems: PendingActionItem[] = [
  {
    action_item_id: "ai1",
    content: "進捗共有メールを送る",
    created_at: "2026-03-20T10:00:00Z",
    record_id: "r1",
    organizer_id: "org-user-id-00001",
    conducted_at: "2026-03-20T10:00:00Z",
  },
];

// -- Mock hooks ---------------------------------------------------------------

let scheduleDetailReturn = {
  schedule: mockSchedule as ScheduleDetail | null,
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

const mockDeleteAgenda = vi.fn().mockResolvedValue(true);
let deleteAgendaReturn = {
  deleteAgenda: mockDeleteAgenda,
  isSubmitting: false,
  error: null as string | null,
};

const mockAddComment = vi.fn().mockResolvedValue({ comment_id: "c2" });
let addAgendaCommentReturn = {
  addComment: mockAddComment,
  isSubmitting: false,
  error: null as string | null,
};

let pendingActionItemsReturn = {
  items: mockPendingItems,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

const mockStartSession = vi.fn().mockResolvedValue({ record_id: "rec-001" });
let startSessionReturn = {
  startSession: mockStartSession,
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

vi.mock("../hooks/useScheduleDetail", () => ({
  useScheduleDetail: () => scheduleDetailReturn,
}));

vi.mock("../hooks/useScheduleAgendas", () => ({
  useScheduleAgendas: () => scheduleAgendasReturn,
}));

vi.mock("../hooks/useAddAgenda", () => ({
  useAddAgenda: () => addAgendaReturn,
}));

vi.mock("../hooks/useDeleteAgenda", () => ({
  useDeleteAgenda: () => deleteAgendaReturn,
}));

vi.mock("../hooks/useAddAgendaComment", () => ({
  useAddAgendaComment: () => addAgendaCommentReturn,
}));

vi.mock("../hooks/usePendingActionItems", () => ({
  usePendingActionItems: () => pendingActionItemsReturn,
}));

vi.mock("../hooks/useStartSession", () => ({
  useStartSession: () => startSessionReturn,
}));

// -- Helpers ------------------------------------------------------------------

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/schedules/s1/preparation"]}>
      <Routes>
        <Route
          path="schedules/:scheduleId/preparation"
          element={<PreparationPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("PreparationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    scheduleDetailReturn = {
      schedule: mockSchedule,
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
    deleteAgendaReturn = {
      deleteAgenda: mockDeleteAgenda,
      isSubmitting: false,
      error: null,
    };
    addAgendaCommentReturn = {
      addComment: mockAddComment,
      isSubmitting: false,
      error: null,
    };
    pendingActionItemsReturn = {
      items: mockPendingItems,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    startSessionReturn = {
      startSession: mockStartSession,
      isSubmitting: false,
      error: null,
    };
  });

  // -- Normal data display --------------------------------------------------

  it("renders the schedule title", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: /Weekly 1on1 -- Tanaka/ }),
    ).toBeInTheDocument();
  });

  it("renders the basic info card", () => {
    renderPage();
    expect(screen.getByText("基本情報")).toBeInTheDocument();
    expect(screen.getByText("confirmed")).toBeInTheDocument();
  });

  it("renders agenda items", () => {
    renderPage();
    expect(screen.getByText("アジェンダ")).toBeInTheDocument();
    expect(
      screen.getByText("前回のアクションアイテム確認"),
    ).toBeInTheDocument();
    expect(screen.getByText("来季の目標設定")).toBeInTheDocument();
  });

  it("renders agenda tags", () => {
    renderPage();
    expect(screen.getByText("テンプレート")).toBeInTheDocument();
    expect(screen.getByText("カウンターパートが追加")).toBeInTheDocument();
  });

  it("renders pending action items", () => {
    renderPage();
    expect(screen.getByText("未完了アクションアイテム")).toBeInTheDocument();
    expect(screen.getByText("進捗共有メールを送る")).toBeInTheDocument();
  });

  it("renders the start session button", () => {
    renderPage();
    expect(
      screen.getByRole("button", { name: "1on1 を開始する" }),
    ).toBeInTheDocument();
  });

  // -- Loading state --------------------------------------------------------

  it("shows loading skeletons when schedule is loading", () => {
    scheduleDetailReturn = {
      ...scheduleDetailReturn,
      schedule: null,
      isLoading: true,
    };
    scheduleAgendasReturn = {
      ...scheduleAgendasReturn,
      agendas: [],
      isLoading: true,
    };
    pendingActionItemsReturn = {
      ...pendingActionItemsReturn,
      items: [],
      isLoading: true,
    };

    const { container } = renderPage();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // -- Error state ----------------------------------------------------------

  it("shows error messages when API calls fail", () => {
    scheduleDetailReturn = {
      ...scheduleDetailReturn,
      schedule: null,
      error: "スケジュールの取得に失敗しました",
    };
    scheduleAgendasReturn = {
      ...scheduleAgendasReturn,
      agendas: [],
      error: "アジェンダの取得に失敗しました",
    };

    renderPage();
    expect(
      screen.getByText("スケジュールの取得に失敗しました"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("アジェンダの取得に失敗しました"),
    ).toBeInTheDocument();
  });

  // -- Add agenda -----------------------------------------------------------

  it("calls addAgenda when submitting a new agenda", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByPlaceholderText("アジェンダを追加...");
    await user.type(input, "新しいアジェンダ");
    const addButton = screen.getByRole("button", { name: "追加" });
    await user.click(addButton);

    expect(mockAddAgenda).toHaveBeenCalledWith("新しいアジェンダ");
  });

  // -- Delete agenda --------------------------------------------------------

  it("calls deleteAgenda when clicking delete button", async () => {
    const user = userEvent.setup();
    renderPage();

    const deleteButtons = screen.getAllByRole("button", {
      name: /を削除$/,
    });
    await user.click(deleteButtons[0]);

    expect(mockDeleteAgenda).toHaveBeenCalledWith("a1");
  });

  // -- Start session --------------------------------------------------------

  it("navigates to recording page when starting session", async () => {
    const user = userEvent.setup();
    renderPage();

    const startButton = screen.getByRole("button", {
      name: "1on1 を開始する",
    });
    await user.click(startButton);

    await waitFor(() => {
      expect(mockStartSession).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/records/rec-001/recording");
    });
  });

  // -- Comment display ------------------------------------------------------

  it("shows comments when clicking comment toggle", async () => {
    const user = userEvent.setup();
    renderPage();

    // The second agenda has 1 comment; its comment toggle button shows "1"
    const commentButtons = screen.getAllByRole("button", {
      name: /^(\d+|コメント)$/,
    });
    // Click the one for "来季の目標設定" which has 1 comment
    const commentToggle = commentButtons.find((btn) => btn.textContent === "1");
    expect(commentToggle).toBeDefined();
    await user.click(commentToggle!);

    expect(screen.getByText("現在の達成率は60%ほどです。")).toBeInTheDocument();
  });

  // -- Empty state ----------------------------------------------------------

  it("shows empty message when no agendas", () => {
    scheduleAgendasReturn = {
      ...scheduleAgendasReturn,
      agendas: [],
    };

    renderPage();
    expect(screen.getByText("アジェンダはまだありません")).toBeInTheDocument();
  });

  it("shows empty message when no pending action items", () => {
    pendingActionItemsReturn = {
      ...pendingActionItemsReturn,
      items: [],
    };

    renderPage();
    expect(
      screen.getByText("未完了のアクションアイテムはありません"),
    ).toBeInTheDocument();
  });

  // -- Start session error --------------------------------------------------

  it("shows error when start session fails", () => {
    startSessionReturn = {
      ...startSessionReturn,
      error: "1on1の開始に失敗しました",
    };

    renderPage();
    expect(screen.getByText("1on1の開始に失敗しました")).toBeInTheDocument();
  });
});
