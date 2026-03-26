import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface RecordAgendaListProps {
  confirmedAgendaIds: string[];
  isLoading: boolean;
}

export function RecordAgendaList({
  confirmedAgendaIds,
  isLoading,
}: RecordAgendaListProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>アジェンダ</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="h-5 w-5 rounded bg-muted" />
                <div className="h-4 w-48 rounded bg-muted" />
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
        <CardTitle>アジェンダ</CardTitle>
      </CardHeader>
      <CardContent>
        {confirmedAgendaIds.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            確認済みのアジェンダはありません
          </p>
        ) : (
          <div className="space-y-2">
            {confirmedAgendaIds.map((agendaId) => (
              <div key={agendaId} className="flex items-center gap-3">
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs">
                  &#x2713;
                </div>
                <span className="text-sm">{agendaId}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
