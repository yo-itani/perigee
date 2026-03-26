import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";

interface CounterpartSchedulePayload {
  counterpart_id: string;
  scheduled_at: string;
}

interface CreateScheduleGroupPayload {
  title: string;
  counterpart_schedules: CounterpartSchedulePayload[];
  agenda_topics?: string[];
  template_id?: string;
}

interface CreateScheduleGroupResult {
  schedule_group_id: string;
}

interface UseCreateScheduleGroupReturn {
  createScheduleGroup: (
    payload: CreateScheduleGroupPayload,
  ) => Promise<CreateScheduleGroupResult>;
  isLoading: boolean;
  error: ApiError | null;
}

export type {
  CounterpartSchedulePayload,
  CreateScheduleGroupPayload,
  CreateScheduleGroupResult,
};

export function useCreateScheduleGroup(): UseCreateScheduleGroupReturn {
  const { userId } = useCurrentUser();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const createScheduleGroup = useCallback(
    async (
      payload: CreateScheduleGroupPayload,
    ): Promise<CreateScheduleGroupResult> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<CreateScheduleGroupResult>(
          "/schedule-groups",
          userId,
          payload,
        );
        return result;
      } catch (e) {
        const apiError =
          e instanceof ApiError
            ? e
            : new ApiError(0, "Unknown error", String(e));
        setError(apiError);
        throw apiError;
      } finally {
        setIsLoading(false);
      }
    },
    [userId],
  );

  return { createScheduleGroup, isLoading, error };
}
