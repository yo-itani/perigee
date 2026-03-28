import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { getAccessToken } from "@/api/auth-store";

export interface CurrentUser {
  userId: string;
  name: string;
  email: string;
  role: "admin" | "member";
  isActive: boolean;
}

interface UserMeResponse {
  id: string;
  name: string;
  email: string;
  role: "admin" | "member";
  is_active: boolean;
  slack_user_id: string | null;
}

interface UseCurrentUserResult {
  user: CurrentUser | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useCurrentUser(): UseCurrentUserResult {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<UserMeResponse>("/users/me");
      setUser({
        userId: data.id,
        name: data.name,
        email: data.email,
        role: data.role,
        isActive: data.is_active,
      });
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`ユーザー情報の取得に失敗しました (${e.status})`);
      } else {
        setError("ユーザー情報の取得に失敗しました");
      }
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  return { user, isLoading, error, refetch: fetchUser };
}
