import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { CreateUserPayload, User } from "../types";

interface UseCreateUserReturn {
  createUser: (payload: CreateUserPayload) => Promise<User | null>;
  isLoading: boolean;
  error: ApiError | null;
}

export function useCreateUser(): UseCreateUserReturn {
  const { userId } = useCurrentUser();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const createUser = useCallback(
    async (payload: CreateUserPayload): Promise<User | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<User>("/users", userId, payload);
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
    [userId],
  );

  return { createUser, isLoading, error };
}
