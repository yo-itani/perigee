import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router";
import { getAccessToken, setAccessToken } from "@/api/auth-store";
import { refreshApi, RefreshError } from "@/api/auth";

/**
 * Route guard that ensures the user is authenticated.
 *
 * On mount, if no access token is present in memory (e.g. after page refresh),
 * it attempts a silent refresh using the HttpOnly cookie. If the refresh fails,
 * it redirects to the login page.
 */
export function AuthGuard() {
  const [status, setStatus] = useState<
    "checking" | "authenticated" | "unauthenticated"
  >(() => {
    return getAccessToken() ? "authenticated" : "checking";
  });

  useEffect(() => {
    if (status !== "checking") {
      return;
    }

    let cancelled = false;

    const tryRestore = async () => {
      try {
        const result = await refreshApi();
        if (!cancelled) {
          setAccessToken(result.access_token);
          setStatus("authenticated");
        }
      } catch (e) {
        if (!cancelled) {
          if (e instanceof RefreshError) {
            setStatus("unauthenticated");
          } else {
            setStatus("unauthenticated");
          }
        }
      }
    };

    void tryRestore();

    return () => {
      cancelled = true;
    };
  }, [status]);

  if (status === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="h-48 w-96 animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
