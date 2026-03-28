import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { DraftRecordItem, DraftRecordsResponse } from "../types";

interface UseDraftRecordsResult {
  drafts: DraftRecordItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDraftRecords(): UseDraftRecordsResult {
  const [drafts, setDrafts] = useState<DraftRecordItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDrafts = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<DraftRecordsResponse>("/records/drafts");
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
  }, []);

  useEffect(() => {
    void fetchDrafts();
  }, [fetchDrafts]);

  return { drafts, isLoading, error, refetch: fetchDrafts };
}
