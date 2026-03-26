import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBar } from "../status-bar";

describe("StatusBar", () => {
  it("renders children text", () => {
    render(<StatusBar data-testid="bar">Status message</StatusBar>);
    expect(screen.getByTestId("bar")).toHaveTextContent("Status message");
  });

  it("has data-slot attribute", () => {
    render(<StatusBar data-testid="bar">Msg</StatusBar>);
    expect(screen.getByTestId("bar")).toHaveAttribute(
      "data-slot",
      "status-bar",
    );
  });

  it("defaults to info variant", () => {
    render(<StatusBar data-testid="bar">Info</StatusBar>);
    const cls = screen.getByTestId("bar").className;
    expect(cls).toContain("bg-info-bg");
    expect(cls).toContain("text-info-text");
  });

  it("applies success variant", () => {
    render(
      <StatusBar data-testid="bar" variant="success">
        OK
      </StatusBar>,
    );
    const cls = screen.getByTestId("bar").className;
    expect(cls).toContain("bg-success-bg");
    expect(cls).toContain("text-success-text");
  });

  it("renders a status dot indicator", () => {
    const { container } = render(<StatusBar>Msg</StatusBar>);
    const dot = container.querySelector(".rounded-full.bg-current");
    expect(dot).toBeInTheDocument();
  });
});
