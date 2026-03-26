import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface CounterpartScheduleData {
  counterpartId: string;
  counterpartName: string;
  startDate: string;
  startTime: string;
  durationMinutes: number;
}

interface CounterpartScheduleBlockProps {
  data: CounterpartScheduleData;
  onChange: (data: CounterpartScheduleData) => void;
  onRemove: () => void;
}

const DURATION_OPTIONS = [
  { value: 30, label: "30分" },
  { value: 60, label: "60分" },
  { value: 90, label: "90分" },
];


export function CounterpartScheduleBlock({
  data,
  onChange,
  onRemove,
}: CounterpartScheduleBlockProps) {
  const avatarChar = data.counterpartName.charAt(0) || "?";

  const handleFieldChange = (
    field: keyof CounterpartScheduleData,
    value: string | number,
  ) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className="rounded-lg border border-border">
      <div className="flex items-center gap-3 border-b border-border px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium">
          {avatarChar}
        </div>
        <span className="flex-1 text-sm font-medium">
          {data.counterpartName}
        </span>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={onRemove}
          aria-label={`${data.counterpartName} を削除`}
        >
          x
        </Button>
      </div>
      <div className="flex flex-wrap gap-4 px-4 py-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">開始日</label>
          <Input
            type="date"
            value={data.startDate}
            onChange={(e) => handleFieldChange("startDate", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">時刻</label>
          <Input
            type="time"
            value={data.startTime}
            onChange={(e) => handleFieldChange("startTime", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground">所要時間</label>
          <select
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            value={data.durationMinutes}
            onChange={(e) =>
              handleFieldChange("durationMinutes", Number(e.target.value))
            }
          >
            {DURATION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
