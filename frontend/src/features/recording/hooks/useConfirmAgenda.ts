import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { ConfirmAgendaResponse } from "../types";

interface UseConfirmAgendaResult {
  confirmAgenda: (agendaId: string) => Promise<ConfirmAgendaResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useConfirmAgenda(recordId: string): UseConfirmAgendaResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmAgenda = useCallback(
    async (agendaId: string): Promise<ConfirmAgendaResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<ConfirmAgendaResponse>(
          `/records/${recordId}/agendas/${agendaId}/confirm`,
          userId,
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`アジェンダの確認に失敗しました (${e.status})`);
        } else {
          setError("アジェンダの確認に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [recordId, userId],
  );

  return { confirmAgenda, isSubmitting, error };
}
