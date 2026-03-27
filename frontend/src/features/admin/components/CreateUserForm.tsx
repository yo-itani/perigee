import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ApiError } from "@/api/client";
import type { CreateUserPayload } from "../types";

interface CreateUserFormProps {
  onSubmit: (payload: CreateUserPayload) => Promise<unknown>;
  isLoading: boolean;
  error: ApiError | null;
}

export function CreateUserForm({
  onSubmit,
  isLoading,
  error,
}: CreateUserFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"admin" | "member">("member");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await onSubmit({ name, email, role });
    if (result) {
      setName("");
      setEmail("");
      setRole("member");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="flex flex-col gap-3">
        <div className="flex gap-3">
          <div className="flex-1">
            <label
              htmlFor="new-user-name"
              className="mb-1.5 block text-sm text-text-subtle"
            >
              名前
            </label>
            <Input
              id="new-user-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="山田 太郎"
              required
            />
          </div>
          <div className="flex-1">
            <label
              htmlFor="new-user-email"
              className="mb-1.5 block text-sm text-text-subtle"
            >
              メール
            </label>
            <Input
              id="new-user-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="taro@example.com"
              required
            />
          </div>
          <div>
            <label
              htmlFor="new-user-role"
              className="mb-1.5 block text-sm text-text-subtle"
            >
              ロール
            </label>
            <select
              id="new-user-role"
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "member")}
              className="h-9 rounded-lg border border-border-subtle bg-surface-secondary px-3 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <option value="member">member</option>
              <option value="admin">admin</option>
            </select>
          </div>
        </div>
        {error && (
          <p className="text-sm text-danger-text">
            ユーザーの追加に失敗しました ({error.status})
          </p>
        )}
        <div>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "追加中..." : "ユーザーを追加"}
          </Button>
        </div>
      </div>
    </form>
  );
}
