import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AgendaTemplateEditor } from "../components/AgendaTemplateEditor";

describe("AgendaTemplateEditor", () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders existing agenda topics", () => {
    render(
      <AgendaTemplateEditor
        agendaTopics={["前回の振り返り", "業務状況の共有"]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    expect(screen.getByText("前回の振り返り")).toBeInTheDocument();
    expect(screen.getByText("業務状況の共有")).toBeInTheDocument();
  });

  it("renders template tags for each topic", () => {
    render(
      <AgendaTemplateEditor
        agendaTopics={["トピック1"]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    expect(screen.getByText("テンプレート")).toBeInTheDocument();
  });

  it("adds a new agenda topic", async () => {
    const user = userEvent.setup();
    render(
      <AgendaTemplateEditor
        agendaTopics={["既存トピック"]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    const input = screen.getByPlaceholderText("アジェンダを追加...");
    await user.type(input, "新しいトピック");
    await user.click(screen.getByRole("button", { name: "追加" }));

    expect(mockOnChange).toHaveBeenCalledWith([
      "既存トピック",
      "新しいトピック",
    ]);
  });

  it("adds a topic when pressing Enter", async () => {
    const user = userEvent.setup();
    render(
      <AgendaTemplateEditor
        agendaTopics={[]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    const input = screen.getByPlaceholderText("アジェンダを追加...");
    await user.type(input, "Enterで追加{Enter}");

    expect(mockOnChange).toHaveBeenCalledWith(["Enterで追加"]);
  });

  it("removes an agenda topic", async () => {
    const user = userEvent.setup();
    render(
      <AgendaTemplateEditor
        agendaTopics={["トピック1", "トピック2"]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "トピック1 を削除" }));

    expect(mockOnChange).toHaveBeenCalledWith(["トピック2"]);
  });

  it("does not add empty topics", async () => {
    const user = userEvent.setup();
    render(
      <AgendaTemplateEditor
        agendaTopics={[]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    const addButton = screen.getByRole("button", { name: "追加" });
    expect(addButton).toBeDisabled();

    const input = screen.getByPlaceholderText("アジェンダを追加...");
    await user.type(input, "   ");
    expect(addButton).toBeDisabled();
  });

  it("clears the input after adding a topic", async () => {
    const user = userEvent.setup();
    render(
      <AgendaTemplateEditor
        agendaTopics={[]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    const input = screen.getByPlaceholderText("アジェンダを追加...");
    await user.type(input, "新しいトピック");
    await user.click(screen.getByRole("button", { name: "追加" }));

    expect(input).toHaveValue("");
  });

  it("renders empty state without topics", () => {
    render(
      <AgendaTemplateEditor
        agendaTopics={[]}
        onAgendaTopicsChange={mockOnChange}
      />,
    );

    expect(
      screen.getByPlaceholderText("アジェンダを追加..."),
    ).toBeInTheDocument();
    expect(screen.queryByText("テンプレート")).not.toBeInTheDocument();
  });
});
