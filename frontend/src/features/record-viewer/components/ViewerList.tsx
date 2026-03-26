import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { RecordViewerRole } from "../types";

interface ViewerListProps {
  viewerIds: string[];
  currentUserId: string;
  counterpartId: string;
  role: RecordViewerRole;
  isLoading: boolean;
  error: string | null;
  onChangeViewers?: () => void;
}

export function ViewerList({
  viewerIds,
  currentUserId,
  counterpartId,
  role,
  isLoading,
  error,
  onChangeViewers,
}: ViewerListProps) {
  const cardTitle = role === "counterpart" ? "この記録の公開先" : "公開先";

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{cardTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-muted" />
                <div className="h-4 w-32 rounded bg-muted" />
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
          <CardTitle>{cardTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  // Viewer role: only show self
  const displayIds =
    role === "viewer"
      ? viewerIds.filter((id) => id === currentUserId)
      : viewerIds;

  // Always include counterpart in the display for organizer/counterpart roles
  const allDisplayIds =
    role !== "viewer" && !displayIds.includes(counterpartId)
      ? [counterpartId, ...displayIds]
      : displayIds;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{cardTitle}</CardTitle>
        {role === "organizer" && onChangeViewers && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onChangeViewers}
            className="text-xs"
          >
            変更する
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {allDisplayIds.length === 0 ? (
          <p className="text-sm text-muted-foreground">公開先はありません</p>
        ) : (
          <div className="space-y-3">
            {allDisplayIds.map((viewerId) => (
              <div key={viewerId} className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium">
                  {viewerId.slice(0, 1).toUpperCase()}
                </div>
                <div className="text-sm">
                  {viewerId}
                  {viewerId === counterpartId && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      カウンターパート
                    </span>
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
