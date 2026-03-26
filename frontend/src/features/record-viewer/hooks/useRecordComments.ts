import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { RecordComment, ListRecordCommentsResponse } from "../types";

interface UseRecordCommentsResult {
  comments: RecordComment[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRecordComments(recordId: string): UseRecordCommentsResult {
  const { userId } = useCurrentUser();
  const [comments, setComments] = useState<RecordComment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchComments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<ListRecordCommentsResponse>(
        `/records/${recordId}/comments`,
        userId,
      );
      setComments(data.comments);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`コメントの取得に失敗しました (${e.status})`);
      } else {
        setError("コメントの取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [recordId, userId]);

  useEffect(() => {
    void fetchComments();
  }, [fetchComments]);

  return { comments, isLoading, error, refetch: fetchComments };
}
