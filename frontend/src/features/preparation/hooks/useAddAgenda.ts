import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { AddAgendaResponse } from "../types";

interface UseAddAgendaResult {
  addAgenda: (topic: string) => Promise<AddAgendaResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useAddAgenda(scheduleId: string): UseAddAgendaResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addAgenda = useCallback(
    async (topic: string): Promise<AddAgendaResponse | null> => {
      if (!scheduleId) {
        setError("スケジュールが指定されていません");
        return null;
      }
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<AddAgendaResponse>(
          `/schedules/${scheduleId}/agendas`,
          { topic },
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`アジェンダの追加に失敗しました (${e.status})`);
        } else {
          setError("アジェンダの追加に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [scheduleId],
  );

  return { addAgenda, isSubmitting, error };
}
