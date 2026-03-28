import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";

interface UseDeleteAgendaResult {
  deleteAgenda: (agendaId: string) => Promise<boolean>;
  isSubmitting: boolean;
  error: string | null;
}

export function useDeleteAgenda(scheduleId: string): UseDeleteAgendaResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deleteAgenda = useCallback(
    async (agendaId: string): Promise<boolean> => {
      setIsSubmitting(true);
      setError(null);
      try {
        await apiClient.delete<void>(
          `/schedules/${scheduleId}/agendas/${agendaId}`,
        );
        return true;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`アジェンダの削除に失敗しました (${e.status})`);
        } else {
          setError("アジェンダの削除に失敗しました");
        }
        return false;
      } finally {
        setIsSubmitting(false);
      }
    },
    [scheduleId],
  );

  return { deleteAgenda, isSubmitting, error };
}
