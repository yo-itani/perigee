import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { PendingActionItem, PendingActionItemsResponse } from "../types";

interface UsePendingActionItemsResult {
  items: PendingActionItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePendingActionItems(): UsePendingActionItemsResult {
  const [items, setItems] = useState<PendingActionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<PendingActionItemsResponse>(
        `/action-items/pending`,
      );
      setItems(data.items);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`アクションアイテムの取得に失敗しました (${e.status})`);
      } else {
        setError("アクションアイテムの取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  return { items, isLoading, error, refetch: fetchItems };
}
