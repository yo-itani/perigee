import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";

interface CounterpartSchedulePayload {
  counterpart_id: string;
  scheduled_at: string;
}

interface CreateFromTemplatePayload {
  template_id: string;
  title: string;
  counterpart_schedules: CounterpartSchedulePayload[];
}

interface CreateFromTemplateResult {
  schedule_group_id: string;
}

interface UseCreateFromTemplateReturn {
  createFromTemplate: (
    payload: CreateFromTemplatePayload,
  ) => Promise<CreateFromTemplateResult>;
  isLoading: boolean;
  error: ApiError | null;
}

export type { CreateFromTemplatePayload, CreateFromTemplateResult };

export function useCreateFromTemplate(): UseCreateFromTemplateReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const createFromTemplate = useCallback(
    async (
      payload: CreateFromTemplatePayload,
    ): Promise<CreateFromTemplateResult> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<CreateFromTemplateResult>(
          "/schedule-groups/from-template",
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
    [],
  );

  return { createFromTemplate, isLoading, error };
}
