import { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useSetupFirstUser } from "../hooks/useSetupFirstUser";

export function SetupPage() {
  const navigate = useNavigate();
  const { isSetupComplete, isLoading: isStatusLoading } = useSystemStatus();
  const { setupUser, isSubmitting, error: submitError } = useSetupFirstUser();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  // Redirect to dashboard if setup is already complete
  if (isSetupComplete === true) {
    void navigate("/", { replace: true });
    return null;
  }

  // Show loading while checking status
  if (isStatusLoading || isSetupComplete === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="h-48 w-96 animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!name.trim()) {
      setValidationError("名前を入力してください");
      return;
    }
    if (!email.trim()) {
      setValidationError("メールアドレスを入力してください");
      return;
    }
    const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    if (!emailPattern.test(email)) {
      setValidationError("有効なメールアドレスを入力してください");
      return;
    }

    const result = await setupUser({ name: name.trim(), email: email.trim() });
    if (result) {
      void navigate("/", { replace: true });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-lg">初期セットアップ</CardTitle>
          <p className="text-sm text-muted-foreground">
            管理者ユーザーを登録してシステムを開始します
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                名前
              </label>
              <Input
                id="name"
                type="text"
                placeholder="管理者の名前"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setValidationError(null);
                }}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                メールアドレス
              </label>
              <Input
                id="email"
                type="text"
                placeholder="admin@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setValidationError(null);
                }}
              />
            </div>

            {validationError && (
              <p className="text-sm text-destructive">{validationError}</p>
            )}
            {submitError && (
              <p className="text-sm text-destructive">{submitError}</p>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "登録中..." : "登録"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
