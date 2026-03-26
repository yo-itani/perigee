import { Link } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { UpcomingScheduleItem } from "../types";
import { formatTime, getRelativeLabel } from "../utils";

interface NextSessionCardProps {
  schedule: UpcomingScheduleItem | null;
  isLoading: boolean;
}

export function NextSessionCard({ schedule, isLoading }: NextSessionCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-24 rounded bg-muted" />
            <div className="h-5 w-48 rounded bg-muted" />
            <div className="h-4 w-36 rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!schedule) {
    return (
      <Card>
        <CardContent>
          <p className="text-muted-foreground">
            予定されている1on1はありません
          </p>
        </CardContent>
      </Card>
    );
  }

  const relativeLabel = getRelativeLabel(schedule.scheduled_at);
  const time = formatTime(schedule.scheduled_at);
  const prepUrl = `/schedules/${schedule.schedule_id}/preparation`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          次の1on1
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-lg font-semibold">{schedule.title}</div>
        <div className="text-sm text-muted-foreground">
          {relativeLabel} {time}
        </div>
        <div className="flex gap-2">
          <Link
            to={prepUrl}
            className="inline-flex h-8 items-center rounded-lg border border-border bg-background px-2.5 text-sm font-medium hover:bg-muted"
          >
            準備画面を開く
          </Link>
          <Link
            to={prepUrl}
            className="inline-flex h-8 items-center rounded-lg bg-primary px-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/80"
          >
            1on1 を開始する
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
