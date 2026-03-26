import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RecordActionItem } from "../types";

interface ActionItemFormProps {
  actionItems: RecordActionItem[];
  onAddActionItem: (title: string, dueDate?: string) => Promise<boolean>;
  onDeleteActionItem: (actionItemId: string) => Promise<void>;
  isAdding: boolean;
  addError: string | null;
  deleteError: string | null;
}

export function ActionItemForm({
  actionItems,
  onAddActionItem,
  onDeleteActionItem,
  isAdding,
  addError,
  deleteError,
}: ActionItemFormProps) {
  const [newTitle, setNewTitle] = useState("");
  const [newDueDate, setNewDueDate] = useState("");

  const handleAdd = async () => {
    const trimmed = newTitle.trim();
    if (!trimmed) return;
    const success = await onAddActionItem(trimmed, newDueDate || undefined);
    if (success) {
      setNewTitle("");
      setNewDueDate("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleAdd();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>アクションアイテム</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {actionItems.map((item) => (
            <div
              key={item.action_item_id}
              className="flex items-center gap-2 rounded-md border p-3"
            >
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium">{item.title}</span>
                {item.due_date && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    期限: {item.due_date}
                  </span>
                )}
              </div>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => void onDeleteActionItem(item.action_item_id)}
                aria-label={`${item.title}を削除`}
              >
                x
              </Button>
            </div>
          ))}
          {actionItems.length === 0 && (
            <p className="text-sm text-muted-foreground">
              アクションアイテムはまだありません
            </p>
          )}
          {deleteError && (
            <p className="text-sm text-destructive" role="alert">
              {deleteError}
            </p>
          )}
          {addError && (
            <p className="text-sm text-destructive" role="alert">
              {addError}
            </p>
          )}
          <div className="flex gap-2 pt-2">
            <Input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="アクションアイテムを追加..."
              className="flex-1"
              disabled={isAdding}
            />
            {/* TODO: API未対応。バックエンドにdue_dateが追加されたら送信値として連携する */}
            <Input
              type="date"
              value={newDueDate}
              onChange={(e) => setNewDueDate(e.target.value)}
              className="w-40"
              disabled={isAdding}
              aria-label="期限"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleAdd()}
              disabled={isAdding || !newTitle.trim()}
            >
              追加
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
