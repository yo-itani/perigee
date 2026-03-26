import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AvatarCircle } from "../avatar-circle";

describe("AvatarCircle", () => {
  it("renders initials text", () => {
    render(<AvatarCircle initials="AB" data-testid="avatar" />);
    expect(screen.getByTestId("avatar")).toHaveTextContent("AB");
  });

  it("has data-slot attribute", () => {
    render(<AvatarCircle initials="X" data-testid="avatar" />);
    expect(screen.getByTestId("avatar")).toHaveAttribute(
      "data-slot",
      "avatar-circle",
    );
  });

  it("defaults to info variant with size-7", () => {
    render(<AvatarCircle initials="T" data-testid="avatar" />);
    const cls = screen.getByTestId("avatar").className;
    expect(cls).toContain("bg-info-bg");
    expect(cls).toContain("size-7");
  });

  it("applies lg size with size-8", () => {
    render(<AvatarCircle initials="T" size="lg" data-testid="avatar" />);
    expect(screen.getByTestId("avatar").className).toContain("size-8");
  });

  it("applies warn variant", () => {
    render(<AvatarCircle initials="W" variant="warn" data-testid="avatar" />);
    const cls = screen.getByTestId("avatar").className;
    expect(cls).toContain("bg-warning-bg");
    expect(cls).toContain("text-warning-text");
  });

  it("applies success variant", () => {
    render(
      <AvatarCircle initials="S" variant="success" data-testid="avatar" />,
    );
    const cls = screen.getByTestId("avatar").className;
    expect(cls).toContain("bg-success-bg");
    expect(cls).toContain("text-success-text");
  });
});
