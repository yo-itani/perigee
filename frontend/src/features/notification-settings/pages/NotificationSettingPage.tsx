import { useNotificationSetting } from "../hooks/useNotificationSetting";
import { useUpdateNotificationSetting } from "../hooks/useUpdateNotificationSetting";
import { NotificationSettingForm } from "../components/NotificationSettingForm";

export function NotificationSettingPage() {
  const {
    setting,
    isLoading,
    error: fetchError,
    refetch,
  } = useNotificationSetting();

  const {
    updateSetting,
    isSubmitting,
    error: updateError,
  } = useUpdateNotificationSetting();

  const handleSave = async (
    isEnabled: boolean,
    reminderMinutesBefore: number,
  ) => {
    const result = await updateSetting({
      is_enabled: isEnabled,
      reminder_minutes_before: reminderMinutesBefore,
    });
    if (result) {
      refetch();
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">通知設定</h1>
        <p className="mt-1 text-muted-foreground">
          リマインド通知の設定を管理します
        </p>
      </div>

      {isLoading && (
        <div className="space-y-4">
          <div className="h-48 animate-pulse rounded-xl bg-muted" />
        </div>
      )}

      {fetchError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{fetchError}</p>
        </div>
      )}

      {!isLoading && !fetchError && setting && (
        <NotificationSettingForm
          isEnabled={setting.is_enabled}
          reminderMinutesBefore={setting.reminder_minutes_before}
          onSave={(enabled, minutes) => void handleSave(enabled, minutes)}
          isSubmitting={isSubmitting}
          submitError={updateError}
        />
      )}
    </div>
  );
}
