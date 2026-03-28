import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { NotificationSetting } from "../types";

interface UseNotificationSettingResult {
  setting: NotificationSetting | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useNotificationSetting(): UseNotificationSettingResult {
  const [setting, setSetting] = useState<NotificationSetting | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSetting = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<NotificationSetting>(
        "/notification-settings",
      );
      setSetting(data);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`通知設定の取得に失敗しました (${e.status})`);
      } else {
        setError("通知設定の取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchSetting();
  }, [fetchSetting]);

  return { setting, isLoading, error, refetch: fetchSetting };
}
