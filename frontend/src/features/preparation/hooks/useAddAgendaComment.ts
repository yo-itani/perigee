import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { AddAgendaCommentResponse } from "../types";

interface UseAddAgendaCommentResult {
  addComment: (
    agendaId: string,
    body: string,
  ) => Promise<AddAgendaCommentResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useAddAgendaComment(): UseAddAgendaCommentResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addComment = useCallback(
    async (
      agendaId: string,
      body: string,
    ): Promise<AddAgendaCommentResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<AddAgendaCommentResponse>(
          `/agendas/${agendaId}/comments`,
          userId,
          { body },
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`コメントの追加に失敗しました (${e.status})`);
        } else {
          setError("コメントの追加に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [userId],
  );

  return { addComment, isSubmitting, error };
}
