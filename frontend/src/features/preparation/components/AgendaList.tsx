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
import type { AgendaItem } from "../types";
import { getAddedByTagLabel } from "../utils";
import { AgendaCommentThread } from "./AgendaCommentThread";

interface AgendaListProps {
  agendas: AgendaItem[];
  isLoading: boolean;
  error: string | null;
  onAddAgenda: (topic: string) => Promise<boolean>;
  onDeleteAgenda: (agendaId: string) => Promise<void>;
  onAddComment: (agendaId: string, body: string) => Promise<boolean>;
  isAddingAgenda: boolean;
  isAddingComment: boolean;
  addAgendaError?: string | null;
  deleteAgendaError?: string | null;
  addCommentError?: string | null;
}

export function AgendaList({
  agendas,
  isLoading,
  error,
  onAddAgenda,
  onDeleteAgenda,
  onAddComment,
  isAddingAgenda,
  isAddingComment,
  addAgendaError,
  deleteAgendaError,
  addCommentError,
}: AgendaListProps) {
  const [newTopic, setNewTopic] = useState("");
  const [expandedAgendaIds, setExpandedAgendaIds] = useState<Set<string>>(
    new Set(),
  );

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

  const toggleComments = (agendaId: string) => {
    setExpandedAgendaIds((prev) => {
      const next = new Set(prev);
      if (next.has(agendaId)) {
        next.delete(agendaId);
      } else {
        next.add(agendaId);
      }
      return next;
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>アジェンダ</CardTitle>
        <CardDescription>
          オーガナイザー・カウンターパートどちらでも追加・コメント可
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="flex-1 space-y-1">
                  <div className="h-4 w-48 rounded bg-muted" />
                  <div className="h-3 w-24 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!isLoading && !error && (
          <div className="space-y-2">
            {agendas.map((agenda) => (
              <div key={agenda.agenda_id} className="rounded-md border p-3">
                <div className="flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium">{agenda.topic}</span>
                    <span className="ml-2 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                      {getAddedByTagLabel(agenda.added_by_tag)}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={() => toggleComments(agenda.agenda_id)}
                  >
                    {agenda.comments.length > 0
                      ? `${agenda.comments.length}`
                      : "コメント"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={() => void onDeleteAgenda(agenda.agenda_id)}
                    aria-label={`${agenda.topic}を削除`}
                  >
                    x
                  </Button>
                </div>
                {expandedAgendaIds.has(agenda.agenda_id) && (
                  <AgendaCommentThread
                    comments={agenda.comments}
                    onAddComment={(body) =>
                      onAddComment(agenda.agenda_id, body)
                    }
                    isSubmitting={isAddingComment}
                    error={addCommentError}
                  />
                )}
              </div>
            ))}
            {agendas.length === 0 && (
              <p className="text-sm text-muted-foreground">
                アジェンダはまだありません
              </p>
            )}
            {deleteAgendaError && (
              <p className="text-sm text-destructive" role="alert">
                {deleteAgendaError}
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
                placeholder="アジェンダを追加..."
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
