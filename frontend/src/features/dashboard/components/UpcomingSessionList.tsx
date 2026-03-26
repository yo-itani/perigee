import { Link } from "react-router";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { UpcomingScheduleItem } from "../types";
import { formatDateJa, formatTime, getRelativeLabel } from "../utils";

interface UpcomingSessionListProps {
  schedules: UpcomingScheduleItem[];
  isLoading: boolean;
  error: string | null;
}

export function UpcomingSessionList({
  schedules,
  isLoading,
  error,
}: UpcomingSessionListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>直近の1on1</CardTitle>
        <CardAction>
          <Link
            to="/schedules"
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
                <div className="h-10 w-10 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-32 rounded bg-muted" />
                  <div className="h-3 w-48 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!isLoading && !error && schedules.length === 0 && (
          <p className="text-sm text-muted-foreground">
            予定されている1on1はありません
          </p>
        )}
        {!isLoading && !error && schedules.length > 0 && (
          <div className="space-y-3">
            {schedules.map((schedule) => (
              <Link
                key={schedule.schedule_id}
                to={`/schedules/${schedule.schedule_id}/preparation`}
                className="flex items-center gap-3 rounded-md p-2 transition-colors hover:bg-muted/50"
              >
                <div className="flex-1">
                  <div className="font-medium">{schedule.title}</div>
                  <div className="text-sm text-muted-foreground">
                    {formatDateJa(schedule.scheduled_at)}{" "}
                    {formatTime(schedule.scheduled_at)}
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">
                  {getRelativeLabel(schedule.scheduled_at)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
