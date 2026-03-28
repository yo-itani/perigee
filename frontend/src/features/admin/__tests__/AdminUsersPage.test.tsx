import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AdminUsersPage } from "../pages/AdminUsersPage";

// -- Mock setup ---------------------------------------------------------------

const mockCreateUser = vi.fn();
const mockUpdateUser = vi.fn();
const mockDeactivateUser = vi.fn();
const mockActivateUser = vi.fn();
const mockRefetch = vi.fn();

vi.mock("../hooks/useUsers", () => ({
  useUsers: () => ({
    users: [
      {
        id: "u1",
        name: "Admin User",
        email: "admin@example.com",
        role: "admin",
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "u2",
        name: "Member User",
        email: "member@example.com",
        role: "member",
        is_active: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ],
    total: 2,
    isLoading: false,
    error: null,
    offset: 0,
    limit: 20,
    setOffset: vi.fn(),
    refetch: mockRefetch,
  }),
}));

vi.mock("../hooks/useCreateUser", () => ({
  useCreateUser: () => ({
    createUser: mockCreateUser,
    isLoading: false,
    error: null,
  }),
}));

vi.mock("../hooks/useUpdateUser", () => ({
  useUpdateUser: () => ({
    updateUser: mockUpdateUser,
    isLoading: false,
    error: null,
  }),
}));

vi.mock("../hooks/useDeactivateUser", () => ({
  useDeactivateUser: () => ({
    deactivateUser: mockDeactivateUser,
    isLoading: false,
    error: null,
  }),
}));

vi.mock("../hooks/useActivateUser", () => ({
  useActivateUser: () => ({
    activateUser: mockActivateUser,
    isLoading: false,
    error: null,
  }),
}));

const mockInviteUser = vi.fn();

vi.mock("../hooks/useInviteUser", () => ({
  useInviteUser: () => ({
    inviteUser: mockInviteUser,
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

describe("AdminUsersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRefetch.mockResolvedValue(undefined);
  });

  it("renders the page title", () => {
    render(<AdminUsersPage />);
    expect(
      screen.getByRole("heading", { name: "ユーザー管理" }),
    ).toBeInTheDocument();
  });

  it("renders the user table with users", () => {
    render(<AdminUsersPage />);
    expect(screen.getByText("Admin User")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("Member User")).toBeInTheDocument();
    expect(screen.getByText("member@example.com")).toBeInTheDocument();
  });

  it("renders status badges correctly", () => {
    render(<AdminUsersPage />);
    expect(screen.getByText("有効")).toBeInTheDocument();
    expect(screen.getByText("無効")).toBeInTheDocument();
  });

  it("renders role badges correctly", () => {
    render(<AdminUsersPage />);
    const badges = screen.getAllByText("admin");
    const adminBadge = badges.find(
      (el) => el.getAttribute("data-slot") === "badge",
    );
    expect(adminBadge).toBeInTheDocument();

    const memberBadges = screen.getAllByText("member");
    const memberBadge = memberBadges.find(
      (el) => el.getAttribute("data-slot") === "badge",
    );
    expect(memberBadge).toBeInTheDocument();
  });

  it("renders the create user form", () => {
    render(<AdminUsersPage />);
    expect(screen.getByLabelText("名前")).toBeInTheDocument();
    expect(screen.getByLabelText("メール")).toBeInTheDocument();
    expect(screen.getByLabelText("ロール")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "ユーザーを追加" }),
    ).toBeInTheDocument();
  });

  it("submits the create user form", async () => {
    const user = userEvent.setup();
    mockCreateUser.mockResolvedValueOnce({ id: "u3" });
    render(<AdminUsersPage />);

    await user.type(screen.getByLabelText("名前"), "New User");
    await user.type(screen.getByLabelText("メール"), "new@example.com");
    await user.click(screen.getByRole("button", { name: "ユーザーを追加" }));

    expect(mockCreateUser).toHaveBeenCalledWith({
      name: "New User",
      email: "new@example.com",
      role: "member",
    });
  });

  it("opens edit modal when clicking edit button", async () => {
    const user = userEvent.setup();
    render(<AdminUsersPage />);

    const editButtons = screen.getAllByRole("button", { name: "編集" });
    await user.click(editButtons[0]);

    expect(
      screen.getByRole("dialog", { name: "ユーザー編集" }),
    ).toBeInTheDocument();
  });

  it("calls deactivateUser when clicking deactivate button for active user", async () => {
    const user = userEvent.setup();
    mockDeactivateUser.mockResolvedValueOnce({ id: "u1", is_active: false });
    render(<AdminUsersPage />);

    const deactivateButton = screen.getByRole("button", { name: "無効化" });
    await user.click(deactivateButton);

    expect(mockDeactivateUser).toHaveBeenCalledWith("u1");
  });

  it("calls activateUser when clicking activate button for inactive user", async () => {
    const user = userEvent.setup();
    mockActivateUser.mockResolvedValueOnce({ id: "u2", is_active: true });
    render(<AdminUsersPage />);

    const activateButton = screen.getByRole("button", { name: "有効化" });
    await user.click(activateButton);

    expect(mockActivateUser).toHaveBeenCalledWith("u2");
  });

  it("closes edit modal when clicking cancel", async () => {
    const user = userEvent.setup();
    render(<AdminUsersPage />);

    const editButtons = screen.getAllByRole("button", { name: "編集" });
    await user.click(editButtons[0]);

    expect(
      screen.getByRole("dialog", { name: "ユーザー編集" }),
    ).toBeInTheDocument();

    const modal = screen.getByRole("dialog", { name: "ユーザー編集" });
    const cancelButton = within(modal).getByRole("button", {
      name: "キャンセル",
    });
    await user.click(cancelButton);

    expect(
      screen.queryByRole("dialog", { name: "ユーザー編集" }),
    ).not.toBeInTheDocument();
  });
});
