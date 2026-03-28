import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SetPasswordPage } from "../pages/SetPasswordPage";
import * as auth from "@/api/auth";

// -- Mocks --------------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// -- Helpers ------------------------------------------------------------------

function renderPage(initialRoute = "/set-password?token=valid-token") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/set-password" element={<SetPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("SetPasswordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -- No token ---------------------------------------------------------------

  it("shows invalid link message when token is missing", () => {
    renderPage("/set-password");
    expect(
      screen.getByText(
        "招待リンクが無効です。管理者に新しい招待リンクを発行してもらってください。",
      ),
    ).toBeInTheDocument();
  });

  // -- Rendering with token ---------------------------------------------------

  it("renders the password form when token is present", () => {
    renderPage();
    expect(
      screen.getByText("新しいパスワードを設定してください"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("パスワード")).toBeInTheDocument();
    expect(screen.getByLabelText("パスワード（確認）")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "パスワードを設定" }),
    ).toBeInTheDocument();
  });

  // -- Validation errors -------------------------------------------------------

  it("shows error when password is empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));

    expect(
      screen.getByText("パスワードを入力してください"),
    ).toBeInTheDocument();
  });

  it("shows error when password is too short", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("パスワード"), "short");
    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));

    expect(
      screen.getByText("パスワードは8文字以上で入力してください"),
    ).toBeInTheDocument();
  });

  it("shows error when passwords do not match", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("パスワード"), "password123");
    await user.type(
      screen.getByLabelText("パスワード（確認）"),
      "different123",
    );
    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));

    expect(screen.getByText("パスワードが一致しません")).toBeInTheDocument();
  });

  // -- Successful submission ---------------------------------------------------

  it("calls setPasswordApi and shows completion on success", async () => {
    vi.spyOn(auth, "setPasswordApi").mockResolvedValueOnce({
      message: "Password set successfully",
    });

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("パスワード"), "new-password-123");
    await user.type(
      screen.getByLabelText("パスワード（確認）"),
      "new-password-123",
    );
    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));

    await waitFor(() => {
      expect(auth.setPasswordApi).toHaveBeenCalledWith(
        "valid-token",
        "new-password-123",
      );
    });

    expect(await screen.findByText("パスワード設定完了")).toBeInTheDocument();
    expect(
      screen.getByText(
        "パスワードが設定されました。ログイン画面からログインしてください。",
      ),
    ).toBeInTheDocument();
  });

  it("navigates to login when clicking the login button after completion", async () => {
    vi.spyOn(auth, "setPasswordApi").mockResolvedValueOnce({
      message: "Password set successfully",
    });

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("パスワード"), "new-password-123");
    await user.type(
      screen.getByLabelText("パスワード（確認）"),
      "new-password-123",
    );
    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));

    await screen.findByText("パスワード設定完了");

    await user.click(screen.getByRole("button", { name: "ログイン画面へ" }));
    expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
  });

  // -- API errors -------------------------------------------------------------

  it("shows API error message on SetPasswordError", async () => {
    vi.spyOn(auth, "setPasswordApi").mockRejectedValueOnce(
      new auth.SetPasswordError(400, "Invitation token has expired"),
    );

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("パスワード"), "password123");
    await user.type(screen.getByLabelText("パスワード（確認）"), "password123");
    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));

    expect(
      await screen.findByText("Invitation token has expired"),
    ).toBeInTheDocument();
  });

  it("shows generic error on unknown failure", async () => {
    vi.spyOn(auth, "setPasswordApi").mockRejectedValueOnce(
      new Error("Network error"),
    );

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("パスワード"), "password123");
    await user.type(screen.getByLabelText("パスワード（確認）"), "password123");
    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));

    expect(
      await screen.findByText("パスワードの設定に失敗しました"),
    ).toBeInTheDocument();
  });

  // -- Clears error on input --------------------------------------------------

  it("clears error when user types in password field", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "パスワードを設定" }));
    expect(
      screen.getByText("パスワードを入力してください"),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText("パスワード"), "a");
    expect(
      screen.queryByText("パスワードを入力してください"),
    ).not.toBeInTheDocument();
  });
});
