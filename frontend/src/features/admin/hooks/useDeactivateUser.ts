import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { User } from "../types";

interface UseDeactivateUserReturn {
  deactivateUser: (targetUserId: string) => Promise<User | null>;
  isLoading: boolean;
  error: ApiError | null;
}

export function useDeactivateUser(): UseDeactivateUserReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const deactivateUser = useCallback(
    async (targetUserId: string): Promise<User | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.put<User>(
          `/users/${targetUserId}/deactivate`,
        );
        return result;
      } catch (e) {
        const apiError =
          e instanceof ApiError
            ? e
            : new ApiError(0, "Unknown error", String(e));
        setError(apiError);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { deactivateUser, isLoading, error };
}
