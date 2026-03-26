import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";

interface TemplateListItem {
  template_id: string;
  name: string;
  default_counterpart_ids: string[];
  agenda_topics: string[];
  created_at: string;
  updated_at: string;
}

interface ListTemplatesResponse {
  templates: TemplateListItem[];
}

interface UseTemplatesReturn {
  templates: TemplateListItem[];
  isLoading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
}

export type { TemplateListItem };

export function useTemplates(): UseTemplatesReturn {
  const { userId } = useCurrentUser();
  const [templates, setTemplates] = useState<TemplateListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchTemplates = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<ListTemplatesResponse>(
        "/templates",
        userId,
      );
      setTemplates(result.templates);
    } catch (e) {
      const apiError =
        e instanceof ApiError ? e : new ApiError(0, "Unknown error", String(e));
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void fetchTemplates();
  }, [fetchTemplates]);

  return { templates, isLoading, error, refetch: fetchTemplates };
}
