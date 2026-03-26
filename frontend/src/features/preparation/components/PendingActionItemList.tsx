import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PendingActionItem } from "../types";
import { formatDateShort } from "../utils";

interface PendingActionItemListProps {
  items: PendingActionItem[];
  isLoading: boolean;
  error: string | null;
  onAddToAgenda: (content: string) => void;
}

export function PendingActionItemList({
  items,
  isLoading,
  error,
  onAddToAgenda,
}: PendingActionItemListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>未完了アクションアイテム</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="flex-1 space-y-1">
                  <div className="h-4 w-48 rounded bg-muted" />
                  <div className="h-3 w-32 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!isLoading && !error && items.length === 0 && (
          <p className="text-sm text-muted-foreground">
            未完了のアクションアイテムはありません
          </p>
        )}
        {!isLoading && !error && items.length > 0 && (
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.action_item_id}
                className="flex items-center gap-3 rounded-md border p-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{item.content}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatDateShort(item.conducted_at)}の1on1から
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onAddToAgenda(item.content)}
                >
                  アジェンダに追加
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
