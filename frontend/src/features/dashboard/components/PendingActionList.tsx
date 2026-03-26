import { Link } from "react-router";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { PendingActionItem } from "../types";

interface PendingActionListProps {
  items: PendingActionItem[];
  isLoading: boolean;
  error: string | null;
}

export function PendingActionList({
  items,
  isLoading,
  error,
}: PendingActionListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>未完了アクションアイテム</CardTitle>
        <CardAction>
          <Link
            to="/records"
            className="text-sm text-primary underline-offset-4 hover:underline"
          >
            すべて見る
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="h-6 w-6 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
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
          <div className="space-y-3">
            {items.map((item) => (
              <Link
                key={item.action_item_id}
                to={`/records/${item.record_id}`}
                className="flex items-center gap-3 rounded-md p-2 transition-colors hover:bg-muted/50"
              >
                <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-700">
                  !
                </div>
                <div className="flex-1">
                  <div className="font-medium">{item.content}</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(item.conducted_at).toLocaleDateString("ja-JP")}
                    の1on1から
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
