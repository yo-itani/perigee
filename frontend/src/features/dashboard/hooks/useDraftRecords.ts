import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { DraftRecordItem, DraftRecordsResponse } from "../types";

interface UseDraftRecordsResult {
  drafts: DraftRecordItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDraftRecords(): UseDraftRecordsResult {
  const { userId } = useCurrentUser();
  const [drafts, setDrafts] = useState<DraftRecordItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDrafts = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<DraftRecordsResponse>(
        "/records/drafts",
        userId,
      );
      setDrafts(data.items);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`下書き記録の取得に失敗しました (${e.status})`);
      } else {
        setError("下書き記録の取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void fetchDrafts();
  }, [fetchDrafts]);

  return { drafts, isLoading, error, refetch: fetchDrafts };
}
