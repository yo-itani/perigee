import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";

interface TemplateDetail {
  template_id: string;
  organizer_id: string;
  name: string;
  default_counterpart_ids: string[];
  agenda_topics: string[];
  created_at: string;
  updated_at: string;
}

interface UseTemplateDetailReturn {
  template: TemplateDetail | null;
  isLoading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
}

export type { TemplateDetail };

export function useTemplateDetail(
  templateId: string | null,
): UseTemplateDetailReturn {
  const [template, setTemplate] = useState<TemplateDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchTemplate = useCallback(async () => {
    if (!templateId) {
      setTemplate(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<TemplateDetail>(
        `/templates/${templateId}`,
      );
      setTemplate(result);
    } catch (e) {
      const apiError =
        e instanceof ApiError ? e : new ApiError(0, "Unknown error", String(e));
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [templateId]);

  useEffect(() => {
    void fetchTemplate();
  }, [fetchTemplate]);

  return { template, isLoading, error, refetch: fetchTemplate };
}
