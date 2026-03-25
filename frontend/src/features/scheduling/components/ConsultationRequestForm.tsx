import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ConsultationRequestFormProps {
  onSubmit: (data: ConsultationRequestFormData) => void;
  isSubmitting: boolean;
  submitError: Error | null;
}

export interface ConsultationRequestFormData {
  organizerId: string;
  scheduledAt: string;
  durationMinutes: number;
  title: string;
  agendaText: string;
}

const DURATION_OPTIONS = [
  { value: 30, label: "30分" },
  { value: 60, label: "60分" },
  { value: 90, label: "90分" },
];

export function ConsultationRequestForm({
  onSubmit,
  isSubmitting,
  submitError,
}: ConsultationRequestFormProps) {
  const [organizerId, setOrganizerId] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [title, setTitle] = useState("");
  const [agendaText, setAgendaText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      organizerId,
      scheduledAt,
      durationMinutes,
      title,
      agendaText,
    });
  };

  const isValid =
    organizerId.trim() !== "" &&
    scheduledAt.trim() !== "" &&
    title.trim() !== "";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>相談相手（オーガナイザーを選択）</CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            placeholder="オーガナイザー ID"
            value={organizerId}
            onChange={(e) => setOrganizerId(e.target.value)}
            required
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            日時 <span className="text-xs text-destructive">必須</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">希望日時</label>
              <Input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">所要時間</label>
              <select
                className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Number(e.target.value))}
              >
                {DURATION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            仮押さえとして登録されます。オーガナイザーが承認すると確定します。
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>内容</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">
              相談のタイトル <span className="text-destructive">必須</span>
            </label>
            <Input
              placeholder="例：キャリアについて相談したい"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">
              アジェンダ（任意）
            </label>
            <textarea
              className="min-h-[100px] w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              placeholder="話したいこと・相談したい内容を書いておくとオーガナイザーが準備できます"
              value={agendaText}
              onChange={(e) => setAgendaText(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {submitError && (
        <div
          role="alert"
          className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          エラーが発生しました: {submitError.message}
        </div>
      )}

      <div className="flex justify-end gap-3">
        <Button type="button" variant="ghost">
          キャンセル
        </Button>
        <Button type="submit" disabled={!isValid || isSubmitting}>
          {isSubmitting ? "送信中..." : "リクエストを送る"}
        </Button>
      </div>
    </form>
  );
}
