import { useCallback, useState } from "react";
import { apiClient, ApiError } from "@/api/client";

interface SendConsultationRequestPayload {
  organizer_id: string;
  scheduled_at: string;
  title: string;
  agenda_topics: string[];
}

interface SendConsultationRequestResult {
  schedule_id: string;
}

interface UseSendConsultationRequestReturn {
  sendConsultationRequest: (
    payload: SendConsultationRequestPayload,
  ) => Promise<SendConsultationRequestResult>;
  isLoading: boolean;
  error: ApiError | null;
}

export type { SendConsultationRequestPayload, SendConsultationRequestResult };

export function useSendConsultationRequest(): UseSendConsultationRequestReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const sendConsultationRequest = useCallback(
    async (
      payload: SendConsultationRequestPayload,
    ): Promise<SendConsultationRequestResult> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<SendConsultationRequestResult>(
          "/schedules/consultation-request",
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

  return { sendConsultationRequest, isLoading, error };
}
