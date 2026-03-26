import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";

interface UseDeleteActionItemResult {
  deleteActionItem: (actionItemId: string) => Promise<boolean>;
  isSubmitting: boolean;
  error: string | null;
}

export function useDeleteActionItem(
  recordId: string,
): UseDeleteActionItemResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deleteActionItem = useCallback(
    async (actionItemId: string): Promise<boolean> => {
      setIsSubmitting(true);
      setError(null);
      try {
        await apiClient.delete<void>(
          `/records/${recordId}/action-items/${actionItemId}`,
          userId,
        );
        return true;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`アクションアイテムの削除に失敗しました (${e.status})`);
        } else {
          setError("アクションアイテムの削除に失敗しました");
        }
        return false;
      } finally {
        setIsSubmitting(false);
      }
    },
    [recordId, userId],
  );

  return { deleteActionItem, isSubmitting, error };
}
