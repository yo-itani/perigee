import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { AgendaItem, AgendasResponse } from "../types";

interface UseScheduleAgendasResult {
  agendas: AgendaItem[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useScheduleAgendas(
  scheduleId: string,
): UseScheduleAgendasResult {
  const { userId } = useCurrentUser();
  const [agendas, setAgendas] = useState<AgendaItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgendas = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<AgendasResponse>(
        `/schedules/${scheduleId}/agendas`,
        userId,
      );
      setAgendas(data.agendas);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`アジェンダの取得に失敗しました (${e.status})`);
      } else {
        setError("アジェンダの取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, [scheduleId, userId]);

  useEffect(() => {
    void fetchAgendas();
  }, [fetchAgendas]);

  return { agendas, isLoading, error, refetch: fetchAgendas };
}
