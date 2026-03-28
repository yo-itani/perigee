import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { PublishRecordResponse } from "../types";

interface UsePublishRecordResult {
  publishRecord: () => Promise<PublishRecordResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function usePublishRecord(recordId: string): UsePublishRecordResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const publishRecord =
    useCallback(async (): Promise<PublishRecordResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<PublishRecordResponse>(
          `/records/${recordId}/publish`,
          {},
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
    }, [recordId]);

  return { publishRecord, isSubmitting, error };
}
