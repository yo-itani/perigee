import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { RecordActionItem, RecordViewerRole } from "../types";
import { formatDateShort } from "../utils";

interface RecordActionItemsProps {
  actionItems: RecordActionItem[];
  isLoading: boolean;
  role: RecordViewerRole;
  onComplete: (actionItemId: string) => void;
  isCompleting: boolean;
  completeError: string | null;
}

export function RecordActionItems({
  actionItems,
  isLoading,
  role,
  onComplete,
  isCompleting,
  completeError,
}: RecordActionItemsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>アクションアイテム</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="h-4 w-full rounded bg-muted" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>アクションアイテム</CardTitle>
      </CardHeader>
      <CardContent>
        {completeError && (
          <p className="text-sm text-destructive mb-3">{completeError}</p>
        )}
        {actionItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            アクションアイテムはありません
          </p>
        ) : (
          <div className="space-y-3">
            {actionItems.map((item) => (
              <div
                key={item.action_item_id}
                className="flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {item.is_completed ? (
                    <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs">
                      &#x2713;
                    </div>
                  ) : (
                    <div className="h-5 w-5 shrink-0 rounded-full border-2 border-muted-foreground/30" />
                  )}
                  <span
                    className={`text-sm truncate ${item.is_completed ? "line-through text-muted-foreground" : ""}`}
                  >
                    {item.title}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-muted-foreground">
                    {formatDateShort(item.created_at)}
                  </span>
                  {!item.is_completed && role === "counterpart" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onComplete(item.action_item_id)}
                      disabled={isCompleting}
                      className="text-xs"
                    >
                      完了
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
