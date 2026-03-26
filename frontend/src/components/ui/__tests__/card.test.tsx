import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card, CardTitle } from "../card";

describe("Card", () => {
  it("renders with border-subtle and rounded-xl", () => {
    render(<Card data-testid="card">Content</Card>);
    const cls = screen.getByTestId("card").className;
    expect(cls).toContain("border-border-subtle");
    expect(cls).toContain("rounded-xl");
  });

  it("uses p-5 padding", () => {
    render(<Card data-testid="card">Content</Card>);
    expect(screen.getByTestId("card").className).toContain("p-5");
  });
});

describe("CardTitle", () => {
  it("applies 13px font size and tracking", () => {
    render(<CardTitle data-testid="title">Title</CardTitle>);
    const cls = screen.getByTestId("title").className;
    expect(cls).toContain("text-[13px]");
    expect(cls).toContain("tracking-[0.03em]");
  });

  it("applies text-subtle color", () => {
    render(<CardTitle data-testid="title">Title</CardTitle>);
    expect(screen.getByTestId("title").className).toContain("text-text-subtle");
  });
});
