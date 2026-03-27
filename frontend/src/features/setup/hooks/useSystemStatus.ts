import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/api/client";

interface SystemStatus {
  is_setup_complete: boolean;
}

interface UseSystemStatusResult {
  isSetupComplete: boolean | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

const DEFAULT_BASE_URL = "http://localhost:8000";

function getBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL;
}

export function useSystemStatus(): UseSystemStatusResult {
  const [isSetupComplete, setIsSetupComplete] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${getBaseUrl()}/system/status`);
      if (!response.ok) {
        throw new ApiError(response.status, response.statusText, null);
      }
      const data: SystemStatus = await response.json();
      setIsSetupComplete(data.is_setup_complete);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`システムステータスの取得に失敗しました (${e.status})`);
      } else {
        setError("システムステータスの取得に失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  return { isSetupComplete, isLoading, error, refetch: fetchStatus };
}
