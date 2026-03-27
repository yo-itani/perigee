import { Navigate, Outlet } from "react-router";
import { useSystemStatus } from "../hooks/useSystemStatus";

export function SetupGuard() {
  const { isSetupComplete, isLoading } = useSystemStatus();

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
