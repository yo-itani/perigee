import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { AddRecordCommentResponse } from "../types";

interface UseAddRecordCommentResult {
  addComment: (body: string) => Promise<AddRecordCommentResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useAddRecordComment(
  recordId: string,
): UseAddRecordCommentResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addComment = useCallback(
    async (body: string): Promise<AddRecordCommentResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<AddRecordCommentResponse>(
          `/records/${recordId}/comments`,
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
    [recordId, userId],
  );

  return { addComment, isSubmitting, error };
}
