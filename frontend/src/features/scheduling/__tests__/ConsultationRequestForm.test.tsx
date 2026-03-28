import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ConsultationRequestForm } from "../components/ConsultationRequestForm";
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

describe("ConsultationRequestForm", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all required fields", () => {
    render(
      <ConsultationRequestForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    expect(
      screen.getByText("相談相手（オーガナイザーを選択）"),
    ).toBeInTheDocument();
    expect(screen.getByText("希望日時")).toBeInTheDocument();
    expect(screen.getByText("所要時間")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/キャリアについて/)).toBeInTheDocument();
  });

  it("disables submit when required fields are empty", () => {
    render(
      <ConsultationRequestForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    const submitButton = screen.getByRole("button", {
      name: "リクエストを送る",
    });
    expect(submitButton).toBeDisabled();
  });

  it("shows submitting state", () => {
    render(
      <ConsultationRequestForm
        onSubmit={mockOnSubmit}
        isSubmitting={true}
        submitError={null}
      />,
    );

    expect(
      screen.getByRole("button", { name: "送信中..." }),
    ).toBeInTheDocument();
  });

  it("displays an error when submission fails", () => {
    const error = new ApiError(400, "Bad Request", {});
    render(
      <ConsultationRequestForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={error}
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/エラーが発生しました/)).toBeInTheDocument();
  });

  it("submits with valid data", async () => {
    const user = userEvent.setup();
    render(
      <ConsultationRequestForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    await user.type(
      screen.getByPlaceholderText("オーガナイザー ID"),
      "organizer-123",
    );
    await user.type(
      screen.getByPlaceholderText(/キャリアについて/),
      "キャリア相談",
    );

    // Fill datetime-local input (find by input type)
    const datetimeInput = document.querySelector(
      'input[type="datetime-local"]',
    ) as HTMLInputElement;
    await user.type(datetimeInput, "2026-04-10T10:00");

    await user.click(screen.getByRole("button", { name: "リクエストを送る" }));

    expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        organizerId: "organizer-123",
        title: "キャリア相談",
      }),
    );
  });

  it("shows helpful hint about tentative registration", () => {
    render(
      <ConsultationRequestForm
        onSubmit={mockOnSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    );

    expect(
      screen.getByText(
        /仮押さえとして登録されます。オーガナイザーが承認すると確定します/,
      ),
    ).toBeInTheDocument();
  });
});
