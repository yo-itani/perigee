import { Card, CardContent } from "@/components/ui/card";

interface MetricsCardsProps {
  weeklyCount: number;
  draftCount: number;
  overdueCount: number;
  isLoading: boolean;
}

export function MetricsCards({
  weeklyCount,
  draftCount,
  overdueCount,
  isLoading,
}: MetricsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <Card key={i}>
            <CardContent>
              <div className="animate-pulse space-y-2">
                <div className="h-3 w-20 rounded bg-muted" />
                <div className="h-6 w-10 rounded bg-muted" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      <Card>
        <CardContent>
          <div className="text-sm text-muted-foreground">今週の1on1</div>
          <div className="mt-1 text-2xl font-bold">{weeklyCount}件</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <div className="text-sm text-muted-foreground">下書き未公開</div>
          <div className="mt-1 text-2xl font-bold text-amber-600">
            {draftCount}件
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            期限切れアクション
          </div>
          <div className="mt-1 text-2xl font-bold text-red-600">
            {overdueCount}件
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
