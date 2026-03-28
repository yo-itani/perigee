import { useNavigate } from "react-router";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { logoutApi } from "@/api/auth";
import { clearAccessToken } from "@/api/auth-store";
import { Button } from "@/components/ui/button";

export function Header() {
  const { user } = useCurrentUser();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logoutApi();
    clearAccessToken();
    void navigate("/login", { replace: true });
  };

  return (
    <header className="flex h-14 items-center border-b border-border px-6">
      <div className="ml-auto flex items-center gap-3">
        <span className="text-sm text-muted-foreground">
          {user?.name ?? ""}
        </span>
        <Button variant="ghost" size="sm" onClick={() => void handleLogout()}>
          ログアウト
        </Button>
      </div>
    </header>
  );
}
