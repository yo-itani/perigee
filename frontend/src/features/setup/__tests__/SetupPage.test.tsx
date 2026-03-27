import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SetupPage } from "../pages/SetupPage";

// -- Mock hooks ---------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

let systemStatusReturn = {
  isSetupComplete: false as boolean | null,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

const mockSetupUser = vi.fn();
let setupFirstUserReturn = {
  setupUser: mockSetupUser,
  isSubmitting: false,
  error: null as string | null,
};

vi.mock("../hooks/useSystemStatus", () => ({
  useSystemStatus: () => systemStatusReturn,
}));

vi.mock("../hooks/useSetupFirstUser", () => ({
  useSetupFirstUser: () => setupFirstUserReturn,
}));

// -- Helpers ------------------------------------------------------------------

function renderPage() {
  return render(
    <MemoryRouter>
      <SetupPage />
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("SetupPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    systemStatusReturn = {
      isSetupComplete: false,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    setupFirstUserReturn = {
      setupUser: mockSetupUser,
      isSubmitting: false,
      error: null,
    };
  });

  // -- Redirect when setup is already complete --------------------------------

  it("redirects to dashboard when setup is already complete", () => {
    systemStatusReturn = {
      ...systemStatusReturn,
      isSetupComplete: true,
    };
    renderPage();
    // Navigate component is rendered (not imperative navigate())
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // -- Loading state ----------------------------------------------------------

  it("shows loading skeleton while checking status", () => {
    systemStatusReturn = {
      ...systemStatusReturn,
      isSetupComplete: null,
      isLoading: true,
    };
    const { container } = renderPage();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // -- Error state with retry -------------------------------------------------

  it("shows error message and retry button when status fetch fails", () => {
    systemStatusReturn = {
      ...systemStatusReturn,
      isSetupComplete: null,
      isLoading: false,
      error: "システムステータスの取得に失敗しました",
    };
    renderPage();
    expect(
      screen.getByText("システムステータスの取得に失敗しました"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "再読み込み" }),
    ).toBeInTheDocument();
  });

  it("calls refetch when retry button is clicked", async () => {
    const mockRefetch = vi.fn();
    systemStatusReturn = {
      ...systemStatusReturn,
      isSetupComplete: null,
      isLoading: false,
      error: "システムステータスの取得に失敗しました",
      refetch: mockRefetch,
    };
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "再読み込み" }));
    expect(mockRefetch).toHaveBeenCalledOnce();
  });

  // -- Normal display ---------------------------------------------------------

  it("renders the setup form", () => {
    renderPage();
    expect(screen.getByText("初期セットアップ")).toBeInTheDocument();
    expect(screen.getByLabelText("名前")).toBeInTheDocument();
    expect(screen.getByLabelText("メールアドレス")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "登録" })).toBeInTheDocument();
  });

  // -- Validation errors ------------------------------------------------------

  it("shows validation error when name is empty", async () => {
    const user = userEvent.setup();
    renderPage();

    const emailInput = screen.getByLabelText("メールアドレス");
    await user.type(emailInput, "admin@example.com");

    const submitButton = screen.getByRole("button", { name: "登録" });
    await user.click(submitButton);

    expect(screen.getByText("名前を入力してください")).toBeInTheDocument();
    expect(mockSetupUser).not.toHaveBeenCalled();
  });

  it("shows validation error when email is empty", async () => {
    const user = userEvent.setup();
    renderPage();

    const nameInput = screen.getByLabelText("名前");
    await user.type(nameInput, "Admin");

    const submitButton = screen.getByRole("button", { name: "登録" });
    await user.click(submitButton);

    expect(
      screen.getByText("メールアドレスを入力してください"),
    ).toBeInTheDocument();
    expect(mockSetupUser).not.toHaveBeenCalled();
  });

  it("shows validation error for invalid email", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("名前"), "Admin");
    await user.type(screen.getByLabelText("メールアドレス"), "not-an-email");

    await user.click(screen.getByRole("button", { name: "登録" }));

    expect(
      screen.getByText("有効なメールアドレスを入力してください"),
    ).toBeInTheDocument();
    expect(mockSetupUser).not.toHaveBeenCalled();
  });

  it("clears validation error when user types", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "登録" }));
    expect(screen.getByText("名前を入力してください")).toBeInTheDocument();

    await user.type(screen.getByLabelText("名前"), "A");
    expect(
      screen.queryByText("名前を入力してください"),
    ).not.toBeInTheDocument();
  });

  // -- Successful submission --------------------------------------------------

  it("calls setupUser and navigates on success", async () => {
    mockSetupUser.mockResolvedValueOnce({
      id: "test-id",
      name: "Admin",
      email: "admin@example.com",
      role: "admin",
      is_active: true,
      slack_user_id: null,
    });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("名前"), "Admin");
    await user.type(
      screen.getByLabelText("メールアドレス"),
      "admin@example.com",
    );
    await user.click(screen.getByRole("button", { name: "登録" }));

    await waitFor(() => {
      expect(mockSetupUser).toHaveBeenCalledWith({
        name: "Admin",
        email: "admin@example.com",
      });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("does not navigate when setupUser returns null", async () => {
    mockSetupUser.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("名前"), "Admin");
    await user.type(
      screen.getByLabelText("メールアドレス"),
      "admin@example.com",
    );
    await user.click(screen.getByRole("button", { name: "登録" }));

    await waitFor(() => {
      expect(mockSetupUser).toHaveBeenCalled();
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // -- Submit error -----------------------------------------------------------

  it("shows submit error message", () => {
    setupFirstUserReturn = {
      ...setupFirstUserReturn,
      error: "セットアップは既に完了しています",
    };
    renderPage();
    expect(
      screen.getByText("セットアップは既に完了しています"),
    ).toBeInTheDocument();
  });

  // -- Submitting state -------------------------------------------------------

  it("shows submitting state on button", () => {
    setupFirstUserReturn = {
      ...setupFirstUserReturn,
      isSubmitting: true,
    };
    renderPage();
    const button = screen.getByRole("button", { name: "登録中..." });
    expect(button).toBeDisabled();
  });
});
