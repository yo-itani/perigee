import { Link } from "react-router";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { NotificationRecord } from "../types";

interface UnreadRecordListProps {
  notifications: NotificationRecord[];
  isLoading: boolean;
  error: string | null;
}

export function UnreadRecordList({
  notifications,
  isLoading,
  error,
}: UnreadRecordListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>未読の記録・コメント</CardTitle>
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
            {[0, 1].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="h-2 w-2 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-48 rounded bg-muted" />
                  <div className="h-3 w-32 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!isLoading && !error && notifications.length === 0 && (
          <p className="text-sm text-muted-foreground">
            未読の記録・コメントはありません
          </p>
        )}
        {!isLoading && !error && notifications.length > 0 && (
          <div className="space-y-3">
            {notifications.map((notification) => (
              <Link
                key={notification.id}
                to={notification.link ?? "/records"}
                className="flex items-center gap-3 rounded-md p-2 transition-colors hover:bg-muted/50"
              >
                <div className="h-2 w-2 flex-shrink-0 rounded-full bg-blue-500" />
                <div className="flex-1">
                  <div className="font-medium">{notification.title}</div>
                  <div className="text-sm text-muted-foreground">
                    {notification.body}
                  </div>
                </div>
                <span className="text-muted-foreground">&rsaquo;</span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
