import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import type { UpdateUserPayload, User } from "../types";

interface UseUpdateUserReturn {
  updateUser: (
    targetUserId: string,
    payload: UpdateUserPayload,
  ) => Promise<User | null>;
  isLoading: boolean;
  error: ApiError | null;
}

export function useUpdateUser(): UseUpdateUserReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const updateUser = useCallback(
    async (
      targetUserId: string,
      payload: UpdateUserPayload,
    ): Promise<User | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.put<User>(
          `/users/${targetUserId}`,
          payload,
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

  return { updateUser, isLoading, error };
}
