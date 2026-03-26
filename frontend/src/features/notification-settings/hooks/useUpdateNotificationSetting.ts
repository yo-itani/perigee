import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type {
  NotificationSetting,
  UpdateNotificationSettingPayload,
} from "../types";

interface UseUpdateNotificationSettingResult {
  updateSetting: (
    payload: UpdateNotificationSettingPayload,
  ) => Promise<NotificationSetting | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useUpdateNotificationSetting(): UseUpdateNotificationSettingResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateSetting = useCallback(
    async (
      payload: UpdateNotificationSettingPayload,
    ): Promise<NotificationSetting | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.put<NotificationSetting>(
          "/notification-settings",
          userId,
          payload,
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`通知設定の更新に失敗しました (${e.status})`);
        } else {
          setError("通知設定の更新に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [userId],
  );

  return { updateSetting, isSubmitting, error };
}
