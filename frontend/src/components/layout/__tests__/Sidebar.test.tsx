import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { Sidebar } from "../Sidebar";

function renderSidebar(initialEntries: string[] = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Sidebar />
    </MemoryRouter>,
  );
}

describe("Sidebar", () => {
  it("renders the app title", () => {
    renderSidebar();
    expect(screen.getByText("perigee")).toBeInTheDocument();
  });

  it("renders all nav group labels", () => {
    renderSidebar();
    // "ダッシュボード" appears as both group label and link, so use getAllByText
    expect(screen.getAllByText("ダッシュボード").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("スケジューリング")).toBeInTheDocument();
    expect(screen.getByText("1on1 実施")).toBeInTheDocument();
    expect(screen.getByText("閲覧・コメント")).toBeInTheDocument();
    expect(screen.getByText("設定")).toBeInTheDocument();
  });

  it("renders all nav items", () => {
    renderSidebar();
    expect(screen.getByRole("link", { name: "ダッシュボード" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "1on1 を設定する" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "準備画面（1on1前）" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "実施・記録画面" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "公開フロー" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "記録閲覧・コメント" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "通知設定" })).toBeInTheDocument();
  });

  it("applies wireframe design tokens to sidebar container", () => {
    const { container } = renderSidebar();
    const aside = container.querySelector("aside");
    expect(aside).toHaveClass("w-[220px]", "bg-background", "border-border-subtle");
  });

  it("applies active style to current route", () => {
    renderSidebar(["/"]);
    const dashboardLink = screen.getByRole("link", { name: "ダッシュボード" });
    expect(dashboardLink).toHaveClass("bg-surface-secondary", "font-medium");
  });

  it("applies inactive style to non-current routes", () => {
    renderSidebar(["/"]);
    const settingsLink = screen.getByRole("link", { name: "通知設定" });
    expect(settingsLink).toHaveClass("text-text-subtle");
    expect(settingsLink).not.toHaveClass("bg-surface-secondary");
  });
});
