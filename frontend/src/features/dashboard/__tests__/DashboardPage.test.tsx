import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DashboardPage } from "../pages/DashboardPage";

// -- Mock hooks ---------------------------------------------------------------

const mockSchedules = [
  {
    schedule_id: "s1",
    organizer_id: "u1",
    counterpart_id: "u2",
    scheduled_at: new Date().toISOString(),
    status: "confirmed",
    title: "Weekly 1on1 -- Tanaka",
    schedule_group_id: null,
  },
];

const mockDrafts = [
  {
    record_id: "r1",
    counterpart_id: "u2",
    conducted_at: "2026-03-20T10:00:00Z",
    memo_excerpt: "Test memo",
    created_at: "2026-03-20T10:00:00Z",
    schedule_id: "s2",
  },
];

const mockPendingItems = [
  {
    action_item_id: "a1",
    content: "Send progress report",
    created_at: "2026-03-20T10:00:00Z",
    record_id: "r2",
    organizer_id: "u1",
    conducted_at: "2026-03-20T10:00:00Z",
  },
];

const mockNotifications = [
  {
    id: "n1",
    recipient_id: "u1",
    notification_type: "record_published",
    title: "Record published",
    body: "A record was published",
    link: "/records/r1",
    is_read: false,
    read_at: null,
    created_at: "2026-03-25T10:00:00Z",
  },
];

let upcomingSchedulesReturn = {
  schedules: mockSchedules,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

let draftRecordsReturn = {
  drafts: mockDrafts,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

let pendingActionItemsReturn = {
  items: mockPendingItems,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

let unreadNotificationsReturn = {
  notifications: mockNotifications,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    userId: "00000000-0000-0000-0000-000000000001",
    name: "Dev User",
  }),
}));

vi.mock("../hooks/useUpcomingSchedules", () => ({
  useUpcomingSchedules: () => upcomingSchedulesReturn,
}));

vi.mock("../hooks/useDraftRecords", () => ({
  useDraftRecords: () => draftRecordsReturn,
}));

vi.mock("../hooks/usePendingActionItems", () => ({
  usePendingActionItems: () => pendingActionItemsReturn,
}));

vi.mock("../hooks/useUnreadNotifications", () => ({
  useUnreadNotifications: () => unreadNotificationsReturn,
}));

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    upcomingSchedulesReturn = {
      schedules: mockSchedules,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    draftRecordsReturn = {
      drafts: mockDrafts,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    pendingActionItemsReturn = {
      items: mockPendingItems,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    unreadNotificationsReturn = {
      notifications: mockNotifications,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
  });

  // -- Normal data display --------------------------------------------------

  it("renders the greeting with user name", () => {
    renderDashboard();
    expect(
      screen.getByRole("heading", { name: /Dev User/ }),
    ).toBeInTheDocument();
  });

  it("renders section titles", () => {
    renderDashboard();
    expect(screen.getByText("次の1on1")).toBeInTheDocument();
    expect(screen.getByText("直近の1on1")).toBeInTheDocument();
    expect(screen.getByText("下書き未公開の記録")).toBeInTheDocument();
    expect(screen.getByText("未完了アクションアイテム")).toBeInTheDocument();
    expect(screen.getByText("未読の記録・コメント")).toBeInTheDocument();
  });

  it("renders the next session card with schedule title", () => {
    renderDashboard();
    const elements = screen.getAllByText("Weekly 1on1 -- Tanaka");
    expect(elements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders metrics cards", () => {
    renderDashboard();
    expect(screen.getByText("今週の1on1")).toBeInTheDocument();
    expect(screen.getByText("下書き未公開")).toBeInTheDocument();
    expect(screen.getByText("期限切れアクション")).toBeInTheDocument();
  });

  it("renders draft records", () => {
    renderDashboard();
    expect(screen.getByText("下書き")).toBeInTheDocument();
    expect(screen.getByText("公開する")).toBeInTheDocument();
  });

  it("renders pending action items", () => {
    renderDashboard();
    expect(screen.getByText("Send progress report")).toBeInTheDocument();
  });

  it("renders unread notifications", () => {
    renderDashboard();
    expect(screen.getByText("Record published")).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    renderDashboard();
    const allLinks = screen.getAllByText("すべて見る");
    expect(allLinks.length).toBeGreaterThanOrEqual(4);
  });

  // -- Loading state --------------------------------------------------------

  it("shows loading skeletons when data is loading", () => {
    upcomingSchedulesReturn = {
      ...upcomingSchedulesReturn,
      schedules: [],
      isLoading: true,
    };
    draftRecordsReturn = {
      ...draftRecordsReturn,
      drafts: [],
      isLoading: true,
    };
    pendingActionItemsReturn = {
      ...pendingActionItemsReturn,
      items: [],
      isLoading: true,
    };
    unreadNotificationsReturn = {
      ...unreadNotificationsReturn,
      notifications: [],
      isLoading: true,
    };

    const { container } = renderDashboard();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // -- Error state ----------------------------------------------------------

  it("shows error messages when API calls fail", () => {
    upcomingSchedulesReturn = {
      ...upcomingSchedulesReturn,
      schedules: [],
      error: "スケジュールの取得に失敗しました",
    };
    draftRecordsReturn = {
      ...draftRecordsReturn,
      drafts: [],
      error: "下書き記録の取得に失敗しました",
    };

    renderDashboard();
    expect(
      screen.getByText("スケジュールの取得に失敗しました"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("下書き記録の取得に失敗しました"),
    ).toBeInTheDocument();
  });

  // -- Empty state ----------------------------------------------------------

  it("shows empty messages when there is no data", () => {
    upcomingSchedulesReturn = {
      ...upcomingSchedulesReturn,
      schedules: [],
    };
    draftRecordsReturn = {
      ...draftRecordsReturn,
      drafts: [],
    };
    pendingActionItemsReturn = {
      ...pendingActionItemsReturn,
      items: [],
    };
    unreadNotificationsReturn = {
      ...unreadNotificationsReturn,
      notifications: [],
    };

    renderDashboard();
    const noScheduleMessages = screen.getAllByText(
      "予定されている1on1はありません",
    );
    expect(noScheduleMessages.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("下書きの記録はありません")).toBeInTheDocument();
    expect(
      screen.getByText("未完了のアクションアイテムはありません"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("未読の記録・コメントはありません"),
    ).toBeInTheDocument();
  });
});
