import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ScheduleDetail } from "../types";
import { formatScheduleDateTime } from "../utils";

interface ScheduleInfoCardProps {
  schedule: ScheduleDetail | null;
  isLoading: boolean;
  error: string | null;
}

export function ScheduleInfoCard({
  schedule,
  isLoading,
  error,
}: ScheduleInfoCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>基本情報</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-3 w-20 rounded bg-muted mb-1" />
                <div className="h-4 w-40 rounded bg-muted" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>基本情報</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!schedule) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>基本情報</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div>
            <div className="text-xs text-muted-foreground">日時</div>
            <div className="text-sm font-medium">
              {formatScheduleDateTime(schedule.scheduled_at)}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">ステータス</div>
            <div className="text-sm font-medium">{schedule.status}</div>
          </div>
        </div>
        <div className="mt-4 border-t pt-4">
          <div className="text-xs text-muted-foreground mb-2">参加者</div>
          <div className="flex gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs">
              {schedule.organizer_id.slice(0, 8)}
              <span className="text-muted-foreground">オーガナイザー</span>
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs">
              {schedule.counterpart_id.slice(0, 8)}
              <span className="text-muted-foreground">カウンターパート</span>
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
