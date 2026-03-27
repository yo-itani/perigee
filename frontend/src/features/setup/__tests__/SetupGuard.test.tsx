import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SetupGuard } from "../components/SetupGuard";

// -- Mock hooks ---------------------------------------------------------------

let systemStatusReturn = {
  isSetupComplete: true as boolean | null,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

vi.mock("../hooks/useSystemStatus", () => ({
  useSystemStatus: () => systemStatusReturn,
}));

// -- Helpers ------------------------------------------------------------------

function renderGuard() {
  return render(
    <MemoryRouter>
      <SetupGuard />
    </MemoryRouter>,
  );
}

// -- Tests --------------------------------------------------------------------

describe("SetupGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    systemStatusReturn = {
      isSetupComplete: true,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
  });

  it("shows loading skeleton while checking status", () => {
    systemStatusReturn = {
      ...systemStatusReturn,
      isSetupComplete: null,
      isLoading: true,
    };
    const { container } = renderGuard();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows error message and retry button when status fetch fails", () => {
    systemStatusReturn = {
      ...systemStatusReturn,
      isSetupComplete: null,
      isLoading: false,
      error: "システムステータスの取得に失敗しました",
    };
    renderGuard();
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
    renderGuard();

    await user.click(screen.getByRole("button", { name: "再読み込み" }));
    expect(mockRefetch).toHaveBeenCalledOnce();
  });
});
