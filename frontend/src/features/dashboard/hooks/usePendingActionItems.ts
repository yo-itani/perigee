import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { PendingActionItem, PendingActionItemsResponse } from "../types";

interface UsePendingActionItemsResult {
  items: PendingActionItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePendingActionItems(): UsePendingActionItemsResult {
  const { userId } = useCurrentUser();
  const [items, setItems] = useState<PendingActionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<PendingActionItemsResponse>(
        `/action-items/pending`,
        userId,
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
  }, [userId]);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  return { items, isLoading, error, refetch: fetchItems };
}
