import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { PublishRecordResponse } from "../types";

interface UsePublishRecordResult {
  publishRecord: (viewerIds: string[]) => Promise<PublishRecordResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function usePublishRecord(recordId: string): UsePublishRecordResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const publishRecord = useCallback(
    async (viewerIds: string[]): Promise<PublishRecordResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<PublishRecordResponse>(
          `/records/${recordId}/publish`,
          userId,
          { viewer_ids: viewerIds },
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`記録の公開に失敗しました (${e.status})`);
        } else {
          setError("記録の公開に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [recordId, userId],
  );

  return { publishRecord, isSubmitting, error };
}
