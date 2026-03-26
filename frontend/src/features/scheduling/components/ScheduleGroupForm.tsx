import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CounterpartScheduleBlock,
  type CounterpartScheduleData,
} from "./CounterpartScheduleBlock";
import { AgendaTemplateEditor } from "./AgendaTemplateEditor";

interface ScheduleGroupFormProps {
  onSubmit: (data: ScheduleGroupFormData) => void | Promise<void>;
  isSubmitting: boolean;
  submitError: Error | null;
}

export interface ScheduleGroupFormData {
  title: string;
  counterpartSchedules: CounterpartScheduleData[];
  agendaTopics: string[];
}

function getDefaultDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function ScheduleGroupForm({
  onSubmit,
  isSubmitting,
  submitError,
}: ScheduleGroupFormProps) {
  const [title, setTitle] = useState("");
  const [counterparts, setCounterparts] = useState<CounterpartScheduleData[]>(
    [],
  );
  const [agendaTopics, setAgendaTopics] = useState<string[]>([]);
  const [newCounterpartId, setNewCounterpartId] = useState("");
  const [newCounterpartName, setNewCounterpartName] = useState("");

  const handleAddCounterpart = () => {
    const id = newCounterpartId.trim();
    const name = newCounterpartName.trim();
    if (!id || !name) return;

    setCounterparts((prev) => [
      ...prev,
      {
        counterpartId: id,
        counterpartName: name,
        startDate: getDefaultDate(),
        startTime: "10:00",
        durationMinutes: 60,
      },
    ]);
    setNewCounterpartId("");
    setNewCounterpartName("");
  };

  const handleRemoveCounterpart = (index: number) => {
    setCounterparts((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCounterpartChange = (
    index: number,
    data: CounterpartScheduleData,
  ) => {
    setCounterparts((prev) =>
      prev.map((item, i) => (i === index ? data : item)),
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await onSubmit({
        title,
        counterpartSchedules: counterparts,
        agendaTopics,
      });
    } catch {
      // エラーは親の submitError 経由で表示される
    }
  };

  const isValid = title.trim() !== "" && counterparts.length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>タイトル</CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            placeholder="例: 週次 1on1"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>カウンターパートごとのスケジュール</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {counterparts.map((cp, index) => (
            <CounterpartScheduleBlock
              key={`${cp.counterpartId}-${index}`}
              data={cp}
              onChange={(data) => handleCounterpartChange(index, data)}
              onRemove={() => handleRemoveCounterpart(index)}
            />
          ))}

          <div className="flex gap-2">
            <Input
              placeholder="カウンターパート ID"
              value={newCounterpartId}
              onChange={(e) => setNewCounterpartId(e.target.value)}
            />
            <Input
              placeholder="カウンターパート名"
              value={newCounterpartName}
              onChange={(e) => setNewCounterpartName(e.target.value)}
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleAddCounterpart}
              disabled={!newCounterpartId.trim() || !newCounterpartName.trim()}
            >
              + 追加
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            テンプレートアジェンダ（任意 / 全カウンターパート共通）
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AgendaTemplateEditor
            agendaTopics={agendaTopics}
            onAgendaTopicsChange={setAgendaTopics}
          />
        </CardContent>
      </Card>

      <div className="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
        カウンターパートごとに別々の日時で1on1が作成されます。アジェンダはテンプレートとして各1on1に適用されます。
      </div>

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
          {isSubmitting ? "送信中..." : "設定して通知する"}
        </Button>
      </div>
    </form>
  );
}
