import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { setPasswordApi, SetPasswordError } from "@/api/auth";

export function SetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-lg">パスワード設定</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-destructive">
              招待リンクが無効です。管理者に新しい招待リンクを発行してもらってください。
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!password) {
      setError("パスワードを入力してください");
      return;
    }
    if (password.length < 8) {
      setError("パスワードは8文字以上で入力してください");
      return;
    }
    if (password !== confirmPassword) {
      setError("パスワードが一致しません");
      return;
    }

    setIsSubmitting(true);
    try {
      await setPasswordApi(token, password);
      setIsComplete(true);
    } catch (e) {
      if (e instanceof SetPasswordError) {
        setError(e.detail);
      } else {
        setError("パスワードの設定に失敗しました");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isComplete) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-lg">パスワード設定完了</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              パスワードが設定されました。ログイン画面からログインしてください。
            </p>
            <Button
              className="w-full"
              onClick={() => void navigate("/login", { replace: true })}
            >
              ログイン画面へ
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-lg">パスワード設定</CardTitle>
          <p className="text-sm text-muted-foreground">
            新しいパスワードを設定してください
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                パスワード
              </label>
              <Input
                id="password"
                type="password"
                placeholder="8文字以上"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError(null);
                }}
                autoComplete="new-password"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="confirm-password" className="text-sm font-medium">
                パスワード（確認）
              </label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="もう一度入力してください"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  setError(null);
                }}
                autoComplete="new-password"
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "設定中..." : "パスワードを設定"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
