import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface RecordMemoProps {
  memo: string;
  isLoading: boolean;
}

export function RecordMemo({ memo, isLoading }: RecordMemoProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>記録（メモ）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            <div className="h-4 w-full rounded bg-muted" />
            <div className="h-4 w-3/4 rounded bg-muted" />
            <div className="h-4 w-5/6 rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>記録（メモ）</CardTitle>
      </CardHeader>
      <CardContent>
        {memo ? (
          <div className="whitespace-pre-line text-sm leading-relaxed">
            {memo}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">メモはまだありません</p>
        )}
      </CardContent>
    </Card>
  );
}
