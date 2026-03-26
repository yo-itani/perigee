import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { AppLayout } from "../AppLayout";

function renderLayout() {
  const router = createMemoryRouter(
    [
      {
        element: <AppLayout />,
        children: [{ index: true, element: <div>Page Content</div> }],
      },
    ],
    { initialEntries: ["/"] },
  );
  return render(<RouterProvider router={router} />);
}

describe("AppLayout", () => {
  it("applies surface background to content area", () => {
    const { container } = renderLayout();
    const contentArea = container.querySelector(".bg-surface");
    expect(contentArea).toBeInTheDocument();
  });

  it("constrains content width with max-w-[680px]", () => {
    const { container } = renderLayout();
    const contentWrapper = container.querySelector(".max-w-\\[680px\\]");
    expect(contentWrapper).toBeInTheDocument();
  });

  it("renders sidebar alongside content", () => {
    const { container } = renderLayout();
    const aside = container.querySelector("aside");
    expect(aside).toBeInTheDocument();
  });
});
