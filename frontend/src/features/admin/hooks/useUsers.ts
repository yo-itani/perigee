import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { User, UsersResponse } from "../types";

interface UseUsersReturn {
  users: User[];
  total: number;
  isLoading: boolean;
  error: ApiError | null;
  offset: number;
  limit: number;
  setOffset: (offset: number) => void;
  refetch: () => Promise<void>;
}

export function useUsers(initialLimit = 20): UseUsersReturn {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = initialLimit;

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<UsersResponse>(
        `/users?offset=${offset}&limit=${limit}`,
      );
      setUsers(result.users);
      setTotal(result.total);
    } catch (e) {
      const apiError =
        e instanceof ApiError ? e : new ApiError(0, "Unknown error", String(e));
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [offset, limit]);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  return {
    users,
    total,
    isLoading,
    error,
    offset,
    limit,
    setOffset,
    refetch: fetchUsers,
  };
}
