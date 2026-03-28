import type { ReactNode } from "react";
import { Navigate } from "react-router";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export function AdminGuard({ children }: { children: ReactNode }) {
  const { user, isLoading } = useCurrentUser();

  if (isLoading) {
    return null;
  }

  if (!user || user.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
