import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { ScheduleDetail } from "../types";

interface UseScheduleDetailResult {
  schedule: ScheduleDetail | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useScheduleDetail(scheduleId: string): UseScheduleDetailResult {
  const [schedule, setSchedule] = useState<ScheduleDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchedule = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<ScheduleDetail>(
        `/schedules/${scheduleId}`,
      );
      setSchedule(data);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`スケジュールの取得に失敗しました (${e.status})`);
      } else {
        setError("スケジュールの取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [scheduleId]);

  useEffect(() => {
    void fetchSchedule();
  }, [fetchSchedule]);

  return { schedule, isLoading, error, refetch: fetchSchedule };
}
