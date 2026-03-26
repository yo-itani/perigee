import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { RecordDetail, RecordViewerRole } from "../types";
import { formatScheduleDateTime } from "../utils";

interface RecordInfoCardProps {
  record: RecordDetail | null;
  role: RecordViewerRole;
  isLoading: boolean;
  error: string | null;
  onEdit?: () => void;
}

export function RecordInfoCard({
  record,
  role,
  isLoading,
  error,
  onEdit,
}: RecordInfoCardProps) {
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

  if (!record) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>基本情報</CardTitle>
        {role === "organizer" && onEdit && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onEdit}
            className="text-xs"
          >
            編集する
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div>
            <div className="text-xs text-muted-foreground">日時</div>
            <div className="text-sm font-medium">
              {formatScheduleDateTime(record.conducted_at)}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">ステータス</div>
            <div className="text-sm font-medium">{record.status}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
