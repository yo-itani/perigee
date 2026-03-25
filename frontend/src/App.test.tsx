import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";

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
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });
});
