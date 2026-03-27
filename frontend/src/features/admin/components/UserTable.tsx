import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { User } from "../types";

interface UserTableProps {
  users: User[];
  onEdit: (user: User) => void;
  onToggleActive: (user: User) => void;
  isToggling: boolean;
}

export function UserTable({
  users,
  onEdit,
  onToggleActive,
  isToggling,
}: UserTableProps) {
  if (users.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-text-muted">
        ユーザーが見つかりません
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border-subtle text-left">
            <th className="pb-2 font-medium text-text-subtle">名前</th>
            <th className="pb-2 font-medium text-text-subtle">メール</th>
            <th className="pb-2 font-medium text-text-subtle">ロール</th>
            <th className="pb-2 font-medium text-text-subtle">ステータス</th>
            <th className="pb-2 font-medium text-text-subtle">操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr
              key={user.id}
              className="border-b border-border-subtle last:border-b-0"
            >
              <td className="py-3 text-foreground">{user.name}</td>
              <td className="py-3 text-text-subtle">{user.email}</td>
              <td className="py-3">
                <Badge variant={user.role === "admin" ? "info" : "gray"}>
                  {user.role}
                </Badge>
              </td>
              <td className="py-3">
                <Badge variant={user.is_active ? "published" : "destructive"}>
                  {user.is_active ? "有効" : "無効"}
                </Badge>
              </td>
              <td className="py-3">
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(user)}
                  >
                    編集
                  </Button>
                  <Button
                    variant={user.is_active ? "danger" : "success"}
                    size="sm"
                    onClick={() => onToggleActive(user)}
                    disabled={isToggling}
                  >
                    {user.is_active ? "無効化" : "有効化"}
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
