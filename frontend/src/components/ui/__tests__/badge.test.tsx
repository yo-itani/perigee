import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "../badge";

describe("Badge", () => {
  it("renders a span element with data-slot", () => {
    render(<Badge data-testid="badge">Label</Badge>);
    const el = screen.getByTestId("badge");
    expect(el.tagName).toBe("SPAN");
    expect(el).toHaveAttribute("data-slot", "badge");
  });

  it("applies draft variant (warning colors)", () => {
    render(
      <Badge data-testid="badge" variant="draft">
        Draft
      </Badge>,
    );
    const cls = screen.getByTestId("badge").className;
    expect(cls).toContain("bg-warning-bg");
    expect(cls).toContain("text-warning-text");
  });

  it("applies published variant (success colors)", () => {
    render(
      <Badge data-testid="badge" variant="published">
        Published
      </Badge>,
    );
    const cls = screen.getByTestId("badge").className;
    expect(cls).toContain("bg-success-bg");
    expect(cls).toContain("text-success-text");
  });

  it("applies info variant", () => {
    render(
      <Badge data-testid="badge" variant="info">
        Info
      </Badge>,
    );
    const cls = screen.getByTestId("badge").className;
    expect(cls).toContain("bg-info-bg");
    expect(cls).toContain("text-info-text");
  });

  it("applies gray variant", () => {
    render(
      <Badge data-testid="badge" variant="gray">
        Gray
      </Badge>,
    );
    const cls = screen.getByTestId("badge").className;
    expect(cls).toContain("bg-surface-secondary");
    expect(cls).toContain("text-text-muted");
  });
});
