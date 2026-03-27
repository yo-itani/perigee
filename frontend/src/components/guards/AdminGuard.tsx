import { Navigate, Outlet } from "react-router";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export function AdminGuard() {
  const { role } = useCurrentUser();

  if (role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
