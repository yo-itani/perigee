import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  MIN_REMINDER_MINUTES,
  MAX_REMINDER_MINUTES,
  validateReminderMinutes,
} from "../utils";

interface NotificationSettingFormProps {
  isEnabled: boolean;
  reminderMinutesBefore: number;
  onSave: (isEnabled: boolean, reminderMinutesBefore: number) => void;
  isSubmitting: boolean;
  submitError: string | null;
}

export function NotificationSettingForm({
  isEnabled,
  reminderMinutesBefore,
  onSave,
  isSubmitting,
  submitError,
}: NotificationSettingFormProps) {
  const [enabled, setEnabled] = useState(isEnabled);
  const [minutes, setMinutes] = useState(String(reminderMinutesBefore));
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSave = () => {
    const minutesNum = Number(minutes);
    const error = validateReminderMinutes(minutesNum);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    onSave(enabled, minutesNum);
  };

  const handleMinutesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMinutes(e.target.value);
    if (validationError) {
      setValidationError(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>通知設定</CardTitle>
        <CardDescription>
          リマインド通知の有効/無効と通知タイミングを設定します
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Toggle */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">リマインド通知</p>
            <p className="text-sm text-muted-foreground">
              1on1の開始前にSlackで通知を受け取ります
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            aria-label="リマインド通知"
            onClick={() => setEnabled(!enabled)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
              enabled ? "bg-primary" : "bg-muted"
            }`}
          >
            <span
              className={`pointer-events-none block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition-transform ${
                enabled ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>

        {/* Reminder minutes */}
        <div className="space-y-2">
          <label htmlFor="reminder-minutes" className="text-sm font-medium">
            リマインド時間（分前）
          </label>
          <div className="flex items-center gap-2">
            <Input
              id="reminder-minutes"
              type="number"
              min={MIN_REMINDER_MINUTES}
              max={MAX_REMINDER_MINUTES}
              value={minutes}
              onChange={handleMinutesChange}
              className="w-24"
              disabled={!enabled}
            />
            <span className="text-sm text-muted-foreground">
              分前に通知（{MIN_REMINDER_MINUTES}〜{MAX_REMINDER_MINUTES}）
            </span>
          </div>
          {validationError && (
            <p className="text-sm text-destructive">{validationError}</p>
          )}
        </div>

        {/* Error and save button */}
        <div className="flex items-center justify-end gap-4">
          {submitError && (
            <p className="text-sm text-destructive">{submitError}</p>
          )}
          <Button onClick={handleSave} disabled={isSubmitting}>
            {isSubmitting ? "保存中..." : "保存"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
