import { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { loginApi, LoginError } from "@/api/auth";
import { setAccessToken } from "@/api/auth-store";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("メールアドレスを入力してください");
      return;
    }
    if (!password) {
      setError("パスワードを入力してください");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await loginApi(email.trim(), password);
      setAccessToken(result.access_token);
      void navigate("/", { replace: true });
    } catch (e) {
      if (e instanceof LoginError) {
        if (e.status === 401) {
          setError("メールアドレスまたはパスワードが正しくありません");
        } else if (e.status === 429) {
          setError(
            "ログイン試行回数が上限に達しました。しばらくしてから再度お試しください",
          );
        } else if (e.status === 403) {
          setError("アカウントが無効化されています");
        } else {
          setError(e.detail);
        }
      } else {
        setError("ログインに失敗しました");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-lg">ログイン</CardTitle>
          <p className="text-sm text-muted-foreground">
            メールアドレスとパスワードを入力してください
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                メールアドレス
              </label>
              <Input
                id="email"
                type="email"
                placeholder="user@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setError(null);
                }}
                autoComplete="email"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                パスワード
              </label>
              <Input
                id="password"
                type="password"
                placeholder="パスワード"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError(null);
                }}
                autoComplete="current-password"
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "ログイン中..." : "ログイン"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
