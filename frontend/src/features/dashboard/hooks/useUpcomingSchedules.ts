import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { UpcomingScheduleItem, UpcomingSchedulesResponse } from "../types";

interface UseUpcomingSchedulesResult {
  schedules: UpcomingScheduleItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useUpcomingSchedules(): UseUpcomingSchedulesResult {
  const { userId } = useCurrentUser();
  const [schedules, setSchedules] = useState<UpcomingScheduleItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchedules = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<UpcomingSchedulesResponse>(
        "/schedules/upcoming",
        userId,
      );
      setSchedules(data.schedules);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`スケジュールの取得に失敗しました (${e.status})`);
      } else {
        setError("スケジュールの取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void fetchSchedules();
  }, [fetchSchedules]);

  return { schedules, isLoading, error, refetch: fetchSchedules };
}
