import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ApiError } from "@/api/client";
import type { UpdateUserPayload, User } from "../types";

interface EditUserModalProps {
  user: User;
  onSubmit: (userId: string, payload: UpdateUserPayload) => Promise<unknown>;
  onClose: () => void;
  isLoading: boolean;
  error: ApiError | null;
}

export function EditUserModal({
  user,
  onSubmit,
  onClose,
  isLoading,
  error,
}: EditUserModalProps) {
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState<"admin" | "member">(user.role);

  useEffect(() => {
    setName(user.name);
    setEmail(user.email);
    setRole(user.role);
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await onSubmit(user.id, { name, email, role });
    if (result) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="ユーザー編集"
    >
      <div
        className="mx-4 w-full max-w-md rounded-xl border border-border-subtle bg-card p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-1 text-base font-medium text-foreground">
          ユーザー編集
        </h2>
        <p className="mb-5 text-sm text-text-subtle">
          ユーザー情報を編集します
        </p>
        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-3">
            <div>
              <label
                htmlFor="edit-user-name"
                className="mb-1.5 block text-sm text-text-subtle"
              >
                名前
              </label>
              <Input
                id="edit-user-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <label
                htmlFor="edit-user-email"
                className="mb-1.5 block text-sm text-text-subtle"
              >
                メール
              </label>
              <Input
                id="edit-user-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label
                htmlFor="edit-user-role"
                className="mb-1.5 block text-sm text-text-subtle"
              >
                ロール
              </label>
              <select
                id="edit-user-role"
                value={role}
                onChange={(e) => setRole(e.target.value as "admin" | "member")}
                className="h-9 w-full rounded-lg border border-border-subtle bg-surface-secondary px-3 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="member">member</option>
                <option value="admin">admin</option>
              </select>
            </div>
            {error && (
              <p className="text-sm text-danger-text">
                ユーザーの更新に失敗しました ({error.status})
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={onClose}>
                キャンセル
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? "保存中..." : "保存"}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
