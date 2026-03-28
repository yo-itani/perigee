import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SchedulingPage } from "../pages/SchedulingPage";

// Mock the hooks
const mockCreateScheduleGroup = vi.fn();
const mockSendConsultationRequest = vi.fn();

vi.mock("../hooks/useCreateScheduleGroup", () => ({
  useCreateScheduleGroup: () => ({
    createScheduleGroup: mockCreateScheduleGroup,
    isLoading: false,
    error: null,
  }),
}));

vi.mock("../hooks/useSendConsultationRequest", () => ({
  useSendConsultationRequest: () => ({
    sendConsultationRequest: mockSendConsultationRequest,
    isLoading: false,
    error: null,
  }),
}));

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

describe("SchedulingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title", () => {
    render(<SchedulingPage />);
    expect(
      screen.getByRole("heading", { name: "1on1 を設定する" }),
    ).toBeInTheDocument();
  });

  it("renders both tabs", () => {
    render(<SchedulingPage />);
    expect(
      screen.getByRole("button", { name: "定期スケジュール型" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "アドホック相談型" }),
    ).toBeInTheDocument();
  });

  it("shows the regular schedule form by default", () => {
    render(<SchedulingPage />);
    expect(
      screen.getByText("カウンターパートごとのスケジュール"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "設定して通知する" }),
    ).toBeInTheDocument();
  });

  it("switches to ad-hoc form when clicking the tab", async () => {
    const user = userEvent.setup();
    render(<SchedulingPage />);

    await user.click(screen.getByRole("button", { name: "アドホック相談型" }));

    expect(
      screen.getByText("相談相手（オーガナイザーを選択）"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "リクエストを送る" }),
    ).toBeInTheDocument();
  });

  it("switches back to regular form", async () => {
    const user = userEvent.setup();
    render(<SchedulingPage />);

    await user.click(screen.getByRole("button", { name: "アドホック相談型" }));
    await user.click(
      screen.getByRole("button", { name: "定期スケジュール型" }),
    );

    expect(
      screen.getByText("カウンターパートごとのスケジュール"),
    ).toBeInTheDocument();
  });
});
