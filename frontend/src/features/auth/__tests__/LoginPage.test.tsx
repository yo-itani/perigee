import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { LoginPage } from "../pages/LoginPage";
import * as auth from "@/api/auth";
import * as authStore from "@/api/auth-store";

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

function renderPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authStore.clearAccessToken();
  });

  // -- Rendering --------------------------------------------------------------

  it("renders the login form", () => {
    renderPage();
    expect(
      screen.getByText("メールアドレスとパスワードを入力してください"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("メールアドレス")).toBeInTheDocument();
    expect(screen.getByLabelText("パスワード")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "ログイン" }),
    ).toBeInTheDocument();
  });

  // -- Validation errors -------------------------------------------------------

  it("shows error when email is empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("パスワード"), "password123");
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    expect(
      screen.getByText("メールアドレスを入力してください"),
    ).toBeInTheDocument();
  });

  it("shows error when password is empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByLabelText("メールアドレス"),
      "user@example.com",
    );
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    expect(
      screen.getByText("パスワードを入力してください"),
    ).toBeInTheDocument();
  });

  // -- Successful login --------------------------------------------------------

  it("calls loginApi and navigates on success", async () => {
    vi.spyOn(auth, "loginApi").mockResolvedValueOnce({
      access_token: "test-access-token",
      token_type: "bearer",
    });

    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByLabelText("メールアドレス"),
      "user@example.com",
    );
    await user.type(screen.getByLabelText("パスワード"), "password123");
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    await waitFor(() => {
      expect(auth.loginApi).toHaveBeenCalledWith(
        "user@example.com",
        "password123",
      );
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });

    expect(authStore.getAccessToken()).toBe("test-access-token");
  });

  // -- Login errors ------------------------------------------------------------

  it("shows error message on 401 (invalid credentials)", async () => {
    vi.spyOn(auth, "loginApi").mockRejectedValueOnce(
      new auth.LoginError(401, "Invalid email or password"),
    );

    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByLabelText("メールアドレス"),
      "user@example.com",
    );
    await user.type(screen.getByLabelText("パスワード"), "wrong");
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    expect(
      await screen.findByText(
        "メールアドレスまたはパスワードが正しくありません",
      ),
    ).toBeInTheDocument();
  });

  it("shows error message on 429 (too many attempts)", async () => {
    vi.spyOn(auth, "loginApi").mockRejectedValueOnce(
      new auth.LoginError(429, "Account locked"),
    );

    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByLabelText("メールアドレス"),
      "user@example.com",
    );
    await user.type(screen.getByLabelText("パスワード"), "password");
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    expect(
      await screen.findByText(
        "ログイン試行回数が上限に達しました。しばらくしてから再度お試しください",
      ),
    ).toBeInTheDocument();
  });

  it("shows error message on 403 (deactivated)", async () => {
    vi.spyOn(auth, "loginApi").mockRejectedValueOnce(
      new auth.LoginError(403, "Account is deactivated"),
    );

    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByLabelText("メールアドレス"),
      "user@example.com",
    );
    await user.type(screen.getByLabelText("パスワード"), "password");
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    expect(
      await screen.findByText("アカウントが無効化されています"),
    ).toBeInTheDocument();
  });

  it("shows generic error on network failure", async () => {
    vi.spyOn(auth, "loginApi").mockRejectedValueOnce(
      new Error("Network error"),
    );

    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByLabelText("メールアドレス"),
      "user@example.com",
    );
    await user.type(screen.getByLabelText("パスワード"), "password");
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    expect(
      await screen.findByText("ログインに失敗しました"),
    ).toBeInTheDocument();
  });

  // -- Clears error on input ---------------------------------------------------

  it("clears error when user types in email field", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "ログイン" }));
    expect(
      screen.getByText("メールアドレスを入力してください"),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText("メールアドレス"), "a");
    expect(
      screen.queryByText("メールアドレスを入力してください"),
    ).not.toBeInTheDocument();
  });

  it("clears error when user types in password field", async () => {
    vi.spyOn(auth, "loginApi").mockRejectedValueOnce(
      new auth.LoginError(401, "Invalid"),
    );

    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByLabelText("メールアドレス"),
      "user@example.com",
    );
    await user.type(screen.getByLabelText("パスワード"), "wrong");
    await user.click(screen.getByRole("button", { name: "ログイン" }));

    await screen.findByText("メールアドレスまたはパスワードが正しくありません");

    await user.type(screen.getByLabelText("パスワード"), "x");
    expect(
      screen.queryByText("メールアドレスまたはパスワードが正しくありません"),
    ).not.toBeInTheDocument();
  });
});
