import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { GetViewersResponse } from "../types";

interface UseRecordViewersResult {
  viewerIds: string[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRecordViewers(recordId: string): UseRecordViewersResult {
  const [viewerIds, setViewerIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchViewers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<GetViewersResponse>(
        `/records/${recordId}/viewers`,
      );
      setViewerIds(data.viewer_ids);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`公開先の取得に失敗しました (${e.status})`);
      } else {
        setError("公開先の取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [recordId]);

  useEffect(() => {
    void fetchViewers();
  }, [fetchViewers]);

  return { viewerIds, isLoading, error, refetch: fetchViewers };
}
