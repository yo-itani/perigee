import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { RecordDetail } from "../types";

interface UseRecordDetailResult {
  record: RecordDetail | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRecordDetail(recordId: string): UseRecordDetailResult {
  const { userId } = useCurrentUser();
  const [record, setRecord] = useState<RecordDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecord = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<RecordDetail>(
        `/records/${recordId}`,
        userId,
      );
      setRecord(data);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`記録の取得に失敗しました (${e.status})`);
      } else {
        setError("記録の取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [recordId, userId]);

  useEffect(() => {
    void fetchRecord();
  }, [fetchRecord]);

  return { record, isLoading, error, refetch: fetchRecord };
}
