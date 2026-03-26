import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "../button";

describe("Button", () => {
  it("renders a button element", () => {
    render(<Button>Click</Button>);
    expect(screen.getByRole("button", { name: "Click" })).toBeInTheDocument();
  });

  it("applies primary variant by default", () => {
    render(<Button data-testid="btn">OK</Button>);
    expect(screen.getByTestId("btn").className).toContain("bg-primary");
  });

  it("applies ghost variant with border-md class", () => {
    render(
      <Button data-testid="btn" variant="ghost">
        Cancel
      </Button>,
    );
    expect(screen.getByTestId("btn").className).toContain("border-border-md");
  });

  it("applies danger variant classes", () => {
    render(
      <Button data-testid="btn" variant="danger">
        Delete
      </Button>,
    );
    const cls = screen.getByTestId("btn").className;
    expect(cls).toContain("border-danger-border");
    expect(cls).toContain("text-danger-text");
  });

  it("applies success variant classes", () => {
    render(
      <Button data-testid="btn" variant="success">
        Done
      </Button>,
    );
    const cls = screen.getByTestId("btn").className;
    expect(cls).toContain("bg-success-bg");
    expect(cls).toContain("text-success-text");
  });
});
