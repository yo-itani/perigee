import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface MemoEditorProps {
  memo: string;
  onMemoChange: (memo: string) => void;
  onSaveMemo: () => void;
  isSaving: boolean;
  error: string | null;
}

export function MemoEditor({
  memo,
  onMemoChange,
  onSaveMemo,
  isSaving,
  error,
}: MemoEditorProps) {
  const handleBlur = () => {
    onSaveMemo();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>メモ</CardTitle>
      </CardHeader>
      <CardContent>
        <textarea
          value={memo}
          onChange={(e) => onMemoChange(e.target.value)}
          onBlur={handleBlur}
          placeholder="1on1中に話した内容をメモしてください。"
          aria-label="メモ"
          className="w-full min-h-[160px] rounded-lg border border-input bg-muted/30 px-3 py-2.5 text-sm leading-relaxed transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 resize-y"
          disabled={isSaving}
        />
        {isSaving && (
          <p className="mt-1 text-xs text-muted-foreground">保存中...</p>
        )}
        {error && (
          <p className="mt-1 text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
