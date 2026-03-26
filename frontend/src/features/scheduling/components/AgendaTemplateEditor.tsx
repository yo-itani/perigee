import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AgendaTemplateEditorProps {
  agendaTopics: string[];
  onAgendaTopicsChange: (topics: string[]) => void;
}

export function AgendaTemplateEditor({
  agendaTopics,
  onAgendaTopicsChange,
}: AgendaTemplateEditorProps) {
  const [newTopic, setNewTopic] = useState("");

  const handleAdd = () => {
    const trimmed = newTopic.trim();
    if (!trimmed) return;
    onAgendaTopicsChange([...agendaTopics, trimmed]);
    setNewTopic("");
  };

  const handleRemove = (index: number) => {
    onAgendaTopicsChange(agendaTopics.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {agendaTopics.map((topic, index) => (
          <div
            key={index}
            className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2"
          >
            <span className="flex-1 text-sm">{topic}</span>
            <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              テンプレート
            </span>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => handleRemove(index)}
              aria-label={`${topic} を削除`}
            >
              x
            </Button>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          placeholder="アジェンダを追加..."
          value={newTopic}
          onChange={(e) => setNewTopic(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <Button
          variant="outline"
          onClick={handleAdd}
          disabled={!newTopic.trim()}
        >
          追加
        </Button>
      </div>
    </div>
  );
}
