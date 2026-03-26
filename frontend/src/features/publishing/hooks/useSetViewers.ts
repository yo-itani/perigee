import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { SetViewersResponse } from "../types";

interface UseSetViewersResult {
  setViewers: (viewerIds: string[]) => Promise<SetViewersResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useSetViewers(recordId: string): UseSetViewersResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setViewers = useCallback(
    async (viewerIds: string[]): Promise<SetViewersResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.put<SetViewersResponse>(
          `/records/${recordId}/viewers`,
          userId,
          { viewer_ids: viewerIds },
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`公開先の設定に失敗しました (${e.status})`);
        } else {
          setError("公開先の設定に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [recordId, userId],
  );

  return { setViewers, isSubmitting, error };
}
