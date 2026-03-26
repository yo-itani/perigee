import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { StartSessionResponse } from "../types";

interface UseStartSessionResult {
  startSession: (
    scheduleId: string,
    conductedAt: string,
  ) => Promise<StartSessionResponse | null>;
  isSubmitting: boolean;
  error: string | null;
}

export function useStartSession(): UseStartSessionResult {
  const { userId } = useCurrentUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSession = useCallback(
    async (
      scheduleId: string,
      conductedAt: string,
    ): Promise<StartSessionResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const data = await apiClient.post<StartSessionResponse>(
          `/records/from-schedule`,
          userId,
          { schedule_id: scheduleId, conducted_at: conductedAt },
        );
        return data;
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`1on1の開始に失敗しました (${e.status})`);
        } else {
          setError("1on1の開始に失敗しました");
        }
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [userId],
  );

  return { startSession, isSubmitting, error };
}
