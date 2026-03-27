import { useCallback, useState } from "react";
import { ApiError } from "@/api/client";

interface SetupFirstUserRequest {
  name: string;
  email: string;
}

interface SetupFirstUserResponse {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  slack_user_id: string | null;
}

interface UseSetupFirstUserResult {
  setupUser: (
    data: SetupFirstUserRequest,
  ) => Promise<SetupFirstUserResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

const DEFAULT_BASE_URL = "http://localhost:8000";

function getBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL;
}

export function useSetupFirstUser(): UseSetupFirstUserResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setupUser = useCallback(
    async (
      data: SetupFirstUserRequest,
    ): Promise<SetupFirstUserResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const response = await fetch(`${getBaseUrl()}/system/setup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        if (!response.ok) {
          let body: unknown;
          try {
            body = await response.json();
          } catch {
            body = await response.text();
          }
          throw new ApiError(response.status, response.statusText, body);
        }
        return (await response.json()) as SetupFirstUserResponse;
      } catch (e) {
        if (e instanceof ApiError) {
          if (e.status === 409) {
            setError("セットアップは既に完了しています");
          } else {
            setError(`ユーザー登録に失敗しました (${e.status})`);
          }
        } else {
          setError("ユーザー登録に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return { setupUser, isSubmitting, error };
}
