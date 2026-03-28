import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { AdminGuard } from "../AdminGuard";

const mockUseCurrentUser = vi.fn();

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => mockUseCurrentUser(),
}));

function renderWithRouter(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<div>Home</div>} />
        <Route
          path="/admin/users"
          element={
            <AdminGuard>
              <div>Admin Users</div>
            </AdminGuard>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AdminGuard", () => {
  it("renders child route when user is admin", () => {
    mockUseCurrentUser.mockReturnValue({
      user: {
        userId: "u1",
        name: "Admin",
        email: "test@example.com",
        role: "admin",
        isActive: true,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter("/admin/users");

    expect(screen.getByText("Admin Users")).toBeInTheDocument();
    expect(screen.queryByText("Home")).not.toBeInTheDocument();
  });

  it("redirects to / when user is not admin", () => {
    mockUseCurrentUser.mockReturnValue({
      user: {
        userId: "u2",
        name: "Member",
        email: "test@example.com",
        role: "member",
        isActive: true,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithRouter("/admin/users");

    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.queryByText("Admin Users")).not.toBeInTheDocument();
  });
});
