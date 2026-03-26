import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";

interface UpdateMemoResponse {
  record_id: string;
}

interface UseUpdateMemoResult {
  updateMemo: (memo: string) => Promise<UpdateMemoResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useUpdateMemo(recordId: string): UseUpdateMemoResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateMemo = useCallback(
    async (memo: string): Promise<UpdateMemoResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.put<UpdateMemoResponse>(
          `/records/${recordId}/memo`,
          userId,
          { memo },
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`メモの保存に失敗しました (${e.status})`);
        } else {
          setError("メモの保存に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [recordId, userId],
  );

  return { updateMemo, isSubmitting, error };
}
