import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { AddActionItemResponse } from "../types";

interface UseAddActionItemResult {
  addActionItem: (title: string) => Promise<AddActionItemResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useAddActionItem(recordId: string): UseAddActionItemResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addActionItem = useCallback(
    async (title: string): Promise<AddActionItemResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<AddActionItemResponse>(
          `/records/${recordId}/action-items`,
          { title },
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`アクションアイテムの追加に失敗しました (${e.status})`);
        } else {
          setError("アクションアイテムの追加に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [recordId],
  );

  return { addActionItem, isSubmitting, error };
}
