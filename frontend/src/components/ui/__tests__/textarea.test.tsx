import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Textarea } from "../textarea";

describe("Textarea", () => {
  it("renders a textarea element", () => {
    render(<Textarea data-testid="ta" />);
    const el = screen.getByTestId("ta");
    expect(el.tagName).toBe("TEXTAREA");
  });

  it("has data-slot attribute", () => {
    render(<Textarea data-testid="ta" />);
    expect(screen.getByTestId("ta")).toHaveAttribute("data-slot", "textarea");
  });

  it("applies surface-secondary background class", () => {
    render(<Textarea data-testid="ta" />);
    expect(screen.getByTestId("ta").className).toContain(
      "bg-surface-secondary",
    );
  });

  it("forwards placeholder prop", () => {
    render(<Textarea placeholder="Enter text" />);
    expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
  });

  it("merges custom className", () => {
    render(<Textarea data-testid="ta" className="custom-class" />);
    expect(screen.getByTestId("ta").className).toContain("custom-class");
  });
});
