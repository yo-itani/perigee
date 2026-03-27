import { Navigate, Outlet } from "react-router";
import { Button } from "@/components/ui/button";
import { useSystemStatus } from "../hooks/useSystemStatus";

export function SetupGuard() {
  const { isSetupComplete, isLoading, error, refetch } = useSystemStatus();

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => void refetch()}>
          再読み込み
        </Button>
      </div>
    );
  }

  if (isLoading || isSetupComplete === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="h-48 w-96 animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  if (!isSetupComplete) {
    return <Navigate to="/setup" replace />;
  }

  return <Outlet />;
}
