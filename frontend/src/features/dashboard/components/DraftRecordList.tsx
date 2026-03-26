import { Link } from "react-router";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DraftRecordItem } from "../types";
import { daysBetween } from "../utils";

interface DraftRecordListProps {
  drafts: DraftRecordItem[];
  isLoading: boolean;
  error: string | null;
}

export function DraftRecordList({
  drafts,
  isLoading,
  error,
}: DraftRecordListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>下書き未公開の記録</CardTitle>
        <CardAction>
          <Link
            to="/records/drafts"
            className="text-sm text-primary underline-offset-4 hover:underline"
          >
            すべて見る
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-40 rounded bg-muted" />
                  <div className="h-3 w-28 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!isLoading && !error && drafts.length === 0 && (
          <p className="text-sm text-muted-foreground">
            下書きの記録はありません
          </p>
        )}
        {!isLoading && !error && drafts.length > 0 && (
          <div className="space-y-3">
            {drafts.map((draft) => {
              const daysAgo = daysBetween(draft.created_at);
              return (
                <div
                  key={draft.record_id}
                  className="flex items-center gap-3 rounded-md p-2"
                >
                  <div className="flex-1">
                    <div className="font-medium">
                      {new Date(draft.conducted_at).toLocaleDateString("ja-JP")}
                      の1on1
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {daysAgo}日間 下書きのまま
                    </div>
                  </div>
                  <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                    下書き
                  </span>
                  <Link
                    to={`/records/${draft.record_id}/publish`}
                    className="inline-flex h-7 items-center rounded-lg px-2.5 text-xs font-medium hover:bg-muted"
                  >
                    公開する
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
