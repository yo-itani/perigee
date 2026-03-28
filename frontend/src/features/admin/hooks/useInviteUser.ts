import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";

interface InvitationResponse {
  token: string;
  expires_at: string;
}

interface UseInviteUserReturn {
  inviteUser: (userId: string) => Promise<InvitationResponse | null>;
  isLoading: boolean;
  error: ApiError | null;
}

export function useInviteUser(): UseInviteUserReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const inviteUser = useCallback(
    async (userId: string): Promise<InvitationResponse | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<InvitationResponse>(
          `/users/${userId}/invite`,
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

  return { inviteUser, isLoading, error };
}
