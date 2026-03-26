import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { SuggestedViewersResponse } from "../types";

interface UseSuggestedViewersResult {
  suggestedViewerIds: string[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useSuggestedViewers(
  recordId: string,
): UseSuggestedViewersResult {
  const { userId } = useCurrentUser();
  const [suggestedViewerIds, setSuggestedViewerIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestedViewers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<SuggestedViewersResponse>(
        `/records/${recordId}/suggested-viewers`,
        userId,
      );
      setSuggestedViewerIds(data.suggested_viewer_ids);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`公開先サジェストの取得に失敗しました (${e.status})`);
      } else {
        setError("公開先サジェストの取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [recordId, userId]);

  useEffect(() => {
    void fetchSuggestedViewers();
  }, [fetchSuggestedViewers]);

  return {
    suggestedViewerIds,
    isLoading,
    error,
    refetch: fetchSuggestedViewers,
  };
}
