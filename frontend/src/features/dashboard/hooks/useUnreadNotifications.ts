import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { NotificationListResponse, NotificationRecord } from "../types";

interface UseUnreadNotificationsResult {
  notifications: NotificationRecord[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useUnreadNotifications(): UseUnreadNotificationsResult {
  const { userId } = useCurrentUser();
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<NotificationListResponse>(
        "/notifications?unread=true",
        userId,
      );
      setNotifications(data.notifications);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`通知の取得に失敗しました (${e.status})`);
      } else {
        setError("通知の取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void fetchNotifications();
  }, [fetchNotifications]);

  return { notifications, isLoading, error, refetch: fetchNotifications };
}
