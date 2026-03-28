import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { NotificationSettingPage } from "../pages/NotificationSettingPage";
import type { NotificationSetting } from "../types";

// -- Mock data ----------------------------------------------------------------

const mockSetting: NotificationSetting = {
  user_id: "00000000-0000-0000-0000-000000000001",
  reminder_minutes_before: 30,
  is_enabled: true,
};

// -- Mock hooks ---------------------------------------------------------------

let notificationSettingReturn = {
  setting: mockSetting as NotificationSetting | null,
  isLoading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

const mockUpdateSetting = vi
  .fn()
  .mockResolvedValue({ ...mockSetting, reminder_minutes_before: 15 });
let updateNotificationSettingReturn = {
  updateSetting: mockUpdateSetting,
  isSubmitting: false,
  error: null as string | null,
};

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

vi.mock("../hooks/useNotificationSetting", () => ({
  useNotificationSetting: () => notificationSettingReturn,
}));

vi.mock("../hooks/useUpdateNotificationSetting", () => ({
  useUpdateNotificationSetting: () => updateNotificationSettingReturn,
}));

// -- Helpers ------------------------------------------------------------------

function renderPage() {
  return render(<NotificationSettingPage />);
}

// -- Tests --------------------------------------------------------------------

describe("NotificationSettingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    notificationSettingReturn = {
      setting: mockSetting,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
    updateNotificationSettingReturn = {
      updateSetting: mockUpdateSetting,
      isSubmitting: false,
      error: null,
    };
  });

  // -- Normal data display --------------------------------------------------

  it("renders the page title", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: "通知設定" }),
    ).toBeInTheDocument();
  });

  it("renders the notification setting form with current values", () => {
    renderPage();
    expect(screen.getByText("リマインド通知")).toBeInTheDocument();
    const minutesInput = screen.getByLabelText("リマインド時間（分前）");
    expect(minutesInput).toHaveValue(30);
  });

  it("renders the toggle in enabled state", () => {
    renderPage();
    const toggle = screen.getByRole("switch", { name: "リマインド通知" });
    expect(toggle).toHaveAttribute("aria-checked", "true");
  });

  it("renders the toggle in disabled state when is_enabled is false", () => {
    notificationSettingReturn = {
      ...notificationSettingReturn,
      setting: { ...mockSetting, is_enabled: false },
    };
    renderPage();
    const toggle = screen.getByRole("switch", { name: "リマインド通知" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
  });

  // -- Loading state --------------------------------------------------------

  it("shows loading skeleton when data is loading", () => {
    notificationSettingReturn = {
      ...notificationSettingReturn,
      setting: null,
      isLoading: true,
    };
    const { container } = renderPage();
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("does not render form when loading", () => {
    notificationSettingReturn = {
      ...notificationSettingReturn,
      setting: null,
      isLoading: true,
    };
    renderPage();
    expect(
      screen.queryByLabelText("リマインド時間（分前）"),
    ).not.toBeInTheDocument();
  });

  // -- Error state ----------------------------------------------------------

  it("shows error message when fetch fails", () => {
    notificationSettingReturn = {
      ...notificationSettingReturn,
      setting: null,
      error: "通知設定の取得に失敗しました (500)",
    };
    renderPage();
    expect(
      screen.getByText("通知設定の取得に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  it("does not render form when fetch fails", () => {
    notificationSettingReturn = {
      ...notificationSettingReturn,
      setting: null,
      error: "通知設定の取得に失敗しました",
    };
    renderPage();
    expect(
      screen.queryByLabelText("リマインド時間（分前）"),
    ).not.toBeInTheDocument();
  });

  // -- Save operation -------------------------------------------------------

  it("calls updateSetting with form values when saving", async () => {
    const user = userEvent.setup();
    renderPage();

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    expect(mockUpdateSetting).toHaveBeenCalledWith({
      is_enabled: true,
      reminder_minutes_before: 30,
    });
  });

  it("calls refetch after successful save", async () => {
    mockUpdateSetting.mockResolvedValueOnce({
      ...mockSetting,
      reminder_minutes_before: 15,
    });
    const user = userEvent.setup();
    renderPage();

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(notificationSettingReturn.refetch).toHaveBeenCalled();
    });
  });

  it("does not call refetch when save fails", async () => {
    mockUpdateSetting.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateSetting).toHaveBeenCalled();
    });

    expect(notificationSettingReturn.refetch).not.toHaveBeenCalled();
  });

  // -- Toggle interaction ---------------------------------------------------

  it("toggles the switch and sends updated value on save", async () => {
    const user = userEvent.setup();
    renderPage();

    const toggle = screen.getByRole("switch", { name: "リマインド通知" });
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-checked", "false");

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    expect(mockUpdateSetting).toHaveBeenCalledWith({
      is_enabled: false,
      reminder_minutes_before: 30,
    });
  });

  // -- Minutes input interaction --------------------------------------------

  it("updates minutes and sends updated value on save", async () => {
    const user = userEvent.setup();
    renderPage();

    const minutesInput = screen.getByLabelText("リマインド時間（分前）");
    await user.clear(minutesInput);
    await user.type(minutesInput, "15");

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    expect(mockUpdateSetting).toHaveBeenCalledWith({
      is_enabled: true,
      reminder_minutes_before: 15,
    });
  });

  // -- Validation -----------------------------------------------------------

  it("shows validation error for out-of-range minutes", async () => {
    const user = userEvent.setup();
    renderPage();

    const minutesInput = screen.getByLabelText("リマインド時間（分前）");
    await user.clear(minutesInput);
    await user.type(minutesInput, "2");

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    expect(
      screen.getByText("リマインド時間は5分から1440分の間で設定してください"),
    ).toBeInTheDocument();
    expect(mockUpdateSetting).not.toHaveBeenCalled();
  });

  it("clears validation error when user changes input", async () => {
    const user = userEvent.setup();
    renderPage();

    const minutesInput = screen.getByLabelText("リマインド時間（分前）");
    await user.clear(minutesInput);
    await user.type(minutesInput, "2");

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    expect(
      screen.getByText("リマインド時間は5分から1440分の間で設定してください"),
    ).toBeInTheDocument();

    await user.clear(minutesInput);
    await user.type(minutesInput, "30");

    expect(
      screen.queryByText("リマインド時間は5分から1440分の間で設定してください"),
    ).not.toBeInTheDocument();
  });

  // -- Update error display ------------------------------------------------

  it("shows update error message", () => {
    updateNotificationSettingReturn = {
      ...updateNotificationSettingReturn,
      error: "通知設定の更新に失敗しました (500)",
    };
    renderPage();
    expect(
      screen.getByText("通知設定の更新に失敗しました (500)"),
    ).toBeInTheDocument();
  });

  // -- Input preserved on error ---------------------------------------------

  it("preserves form values when update fails", async () => {
    mockUpdateSetting.mockResolvedValueOnce(null);
    const user = userEvent.setup();
    renderPage();

    const minutesInput = screen.getByLabelText("リマインド時間（分前）");
    await user.clear(minutesInput);
    await user.type(minutesInput, "60");

    const toggle = screen.getByRole("switch", { name: "リマインド通知" });
    await user.click(toggle);

    const saveButton = screen.getByRole("button", { name: "保存" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateSetting).toHaveBeenCalled();
    });

    // Values should be preserved after failed save
    expect(minutesInput).toHaveValue(60);
    expect(toggle).toHaveAttribute("aria-checked", "false");
  });

  // -- Submitting state -----------------------------------------------------

  it("shows submitting state on save button", () => {
    updateNotificationSettingReturn = {
      ...updateNotificationSettingReturn,
      isSubmitting: true,
    };
    renderPage();
    const saveButton = screen.getByRole("button", { name: "保存中..." });
    expect(saveButton).toBeDisabled();
  });

  // -- Minutes input disabled when toggle is off ----------------------------

  it("disables minutes input when toggle is off", async () => {
    notificationSettingReturn = {
      ...notificationSettingReturn,
      setting: { ...mockSetting, is_enabled: false },
    };
    renderPage();

    const minutesInput = screen.getByLabelText("リマインド時間（分前）");
    expect(minutesInput).toBeDisabled();
  });
});
