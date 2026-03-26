import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";

interface SaveDraftResponse {
  record_id: string;
}

interface UseSaveDraftResult {
  saveDraft: () => Promise<SaveDraftResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useSaveDraft(recordId: string): UseSaveDraftResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saveDraft = useCallback(async (): Promise<SaveDraftResponse | null> => {
    setIsSubmitting(true);
    setError(null);
    try {
      const data = await apiClient.post<SaveDraftResponse>(
        `/records/${recordId}/save-draft`,
        userId,
      );
      return data;
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`下書き保存に失敗しました (${e.status})`);
      } else {
        setError("下書き保存に失敗しました");
      }
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, [recordId, userId]);

  return { saveDraft, isSubmitting, error };
}
