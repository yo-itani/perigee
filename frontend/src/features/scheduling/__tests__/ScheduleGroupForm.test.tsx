import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ScheduleGroupForm } from "../components/ScheduleGroupForm";
import { ApiError } from "@/api/client";

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

describe("ScheduleGroupForm", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the form with required fields", () => {
    render(
      <ScheduleGroupForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    expect(screen.getByText("タイトル")).toBeInTheDocument();
    expect(
      screen.getByText("カウンターパートごとのスケジュール"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "テンプレートアジェンダ（任意 / 全カウンターパート共通）",
      ),
    ).toBeInTheDocument();
  });

  it("disables submit when title is empty", () => {
    render(
      <ScheduleGroupForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    const submitButton = screen.getByRole("button", {
      name: "設定して通知する",
    });
    expect(submitButton).toBeDisabled();
  });

  it("shows submitting state", () => {
    render(
      <ScheduleGroupForm
        onSubmit={mockOnSubmit}
        isSubmitting={true}
        submitError={null}
      />,
    );

    expect(
      screen.getByRole("button", { name: "送信中..." }),
    ).toBeInTheDocument();
  });

  it("displays an error message when submit fails", () => {
    const error = new ApiError(500, "Internal Server Error", {});
    render(
      <ScheduleGroupForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={error}
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/エラーが発生しました/)).toBeInTheDocument();
  });

  it("allows adding a counterpart", async () => {
    const user = userEvent.setup();
    render(
      <ScheduleGroupForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    const idInput = screen.getByPlaceholderText("カウンターパート ID");
    const nameInput = screen.getByPlaceholderText("カウンターパート名");

    await user.type(idInput, "user-123");
    await user.type(nameInput, "田中 太郎");
    await user.click(screen.getByRole("button", { name: "+ 追加" }));

    expect(screen.getByText("田中 太郎")).toBeInTheDocument();
  });

  it("allows removing a counterpart", async () => {
    const user = userEvent.setup();
    render(
      <ScheduleGroupForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    // Add a counterpart first
    await user.type(
      screen.getByPlaceholderText("カウンターパート ID"),
      "user-123",
    );
    await user.type(
      screen.getByPlaceholderText("カウンターパート名"),
      "田中 太郎",
    );
    await user.click(screen.getByRole("button", { name: "+ 追加" }));

    expect(screen.getByText("田中 太郎")).toBeInTheDocument();

    // Remove the counterpart
    await user.click(screen.getByRole("button", { name: "田中 太郎 を削除" }));

    expect(screen.queryByText("田中 太郎")).not.toBeInTheDocument();
  });

  it("submits the form with valid data", async () => {
    const user = userEvent.setup();
    render(
      <ScheduleGroupForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    // Fill title
    await user.type(screen.getByPlaceholderText("例: 週次 1on1"), "週次 1on1");

    // Add counterpart
    await user.type(
      screen.getByPlaceholderText("カウンターパート ID"),
      "user-123",
    );
    await user.type(
      screen.getByPlaceholderText("カウンターパート名"),
      "田中 太郎",
    );
    await user.click(screen.getByRole("button", { name: "+ 追加" }));

    // Submit
    await user.click(screen.getByRole("button", { name: "設定して通知する" }));

    expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "週次 1on1",
        counterpartSchedules: expect.arrayContaining([
          expect.objectContaining({
            counterpartId: "user-123",
            counterpartName: "田中 太郎",
          }),
        ]),
      }),
    );
  });
});
