import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { CompleteActionItemResponse } from "../types";

interface UseCompleteActionItemResult {
  completeItem: (
    actionItemId: string,
  ) => Promise<CompleteActionItemResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useCompleteActionItem(): UseCompleteActionItemResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completeItem = useCallback(
    async (
      actionItemId: string,
    ): Promise<CompleteActionItemResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<CompleteActionItemResponse>(
          `/action-items/${actionItemId}/complete`,
          userId,
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`アクションアイテムの完了に失敗しました (${e.status})`);
        } else {
          setError("アクションアイテムの完了に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [userId],
  );

  return { completeItem, isSubmitting, error };
}
