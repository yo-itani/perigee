import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    user: {
      userId: "00000000-0000-0000-0000-000000000001",
      name: "Dev User",
      email: "dev@example.com",
      role: "admin",
      isActive: true,
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/features/dashboard/hooks/useUpcomingSchedules", () => ({
  useUpcomingSchedules: () => ({
    schedules: [],
    isLoading: false,
    error: null,
  }),
}));

vi.mock("@/features/dashboard/hooks/useDraftRecords", () => ({
  useDraftRecords: () => ({ drafts: [], isLoading: false, error: null }),
}));

vi.mock("@/features/dashboard/hooks/usePendingActionItems", () => ({
  usePendingActionItems: () => ({
    items: [],
    isLoading: false,
    error: null,
  }),
}));

vi.mock("@/features/dashboard/hooks/useUnreadNotifications", () => ({
  useUnreadNotifications: () => ({
    notifications: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

function renderWithProviders(initialEntries: string[] = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  const router = createMemoryRouter(
    [
      {
        element: <AppLayout />,
        children: [{ index: true, element: <DashboardPage /> }],
      },
    ],
    { initialEntries },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("App", () => {
  it("renders the app title in sidebar", () => {
    renderWithProviders();
    expect(screen.getByText("perigee")).toBeInTheDocument();
  });

  it("renders the dashboard page", () => {
    renderWithProviders();
    expect(
      screen.getByRole("heading", { name: /Dev User/ }),
    ).toBeInTheDocument();
  });
});
