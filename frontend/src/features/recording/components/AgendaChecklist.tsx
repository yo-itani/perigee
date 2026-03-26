import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AgendaItem } from "@/features/preparation/types";
import { getAddedByTagLabel } from "../utils";

interface AgendaChecklistProps {
  agendas: AgendaItem[];
  confirmedAgendaIds: string[];
  isLoading: boolean;
  error: string | null;
  onConfirmAgenda: (agendaId: string) => Promise<void>;
  onAddAgenda: (topic: string) => Promise<boolean>;
  isAddingAgenda: boolean;
  confirmError: string | null;
  addAgendaError: string | null;
}

export function AgendaChecklist({
  agendas,
  confirmedAgendaIds,
  isLoading,
  error,
  onConfirmAgenda,
  onAddAgenda,
  isAddingAgenda,
  confirmError,
  addAgendaError,
}: AgendaChecklistProps) {
  const [newTopic, setNewTopic] = useState("");

  const handleAddAgenda = async () => {
    const trimmed = newTopic.trim();
    if (!trimmed) return;
    const success = await onAddAgenda(trimmed);
    if (success) {
      setNewTopic("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleAddAgenda();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>アジェンダ</CardTitle>
        <CardDescription>話し終えたらチェック</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="h-4 w-4 rounded bg-muted" />
                <div className="flex-1 space-y-1">
                  <div className="h-4 w-48 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!isLoading && !error && (
          <div className="space-y-2">
            {agendas.map((agenda) => {
              const isConfirmed = confirmedAgendaIds.includes(agenda.agenda_id);
              return (
                <div
                  key={agenda.agenda_id}
                  className="flex items-center gap-3 rounded-md border p-3"
                >
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={isConfirmed}
                    aria-label={`${agenda.topic}を確認`}
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border text-xs ${
                      isConfirmed
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input"
                    }`}
                    onClick={() => void onConfirmAgenda(agenda.agenda_id)}
                    disabled={isConfirmed}
                  >
                    {isConfirmed && "✓"}
                  </button>
                  <div className="flex-1 min-w-0">
                    <span
                      className={`text-sm font-medium ${isConfirmed ? "line-through text-muted-foreground" : ""}`}
                    >
                      {agenda.topic}
                    </span>
                    <span className="ml-2 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                      {getAddedByTagLabel(agenda.added_by_tag)}
                    </span>
                  </div>
                </div>
              );
            })}
            {agendas.length === 0 && (
              <p className="text-sm text-muted-foreground">
                アジェンダはまだありません
              </p>
            )}
            {confirmError && (
              <p className="text-sm text-destructive" role="alert">
                {confirmError}
              </p>
            )}
            {addAgendaError && (
              <p className="text-sm text-destructive" role="alert">
                {addAgendaError}
              </p>
            )}
            <div className="flex gap-2 pt-2">
              <Input
                value={newTopic}
                onChange={(e) => setNewTopic(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="話題が増えたら追加..."
                className="flex-1"
                disabled={isAddingAgenda}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => void handleAddAgenda()}
                disabled={isAddingAgenda || !newTopic.trim()}
              >
                追加
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
