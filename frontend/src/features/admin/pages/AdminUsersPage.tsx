import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UserTable } from "../components/UserTable";
import { CreateUserForm } from "../components/CreateUserForm";
import { EditUserModal } from "../components/EditUserModal";
import { useUsers } from "../hooks/useUsers";
import { useCreateUser } from "../hooks/useCreateUser";
import { useUpdateUser } from "../hooks/useUpdateUser";
import { useDeactivateUser } from "../hooks/useDeactivateUser";
import { useActivateUser } from "../hooks/useActivateUser";
import type { User } from "../types";

export function AdminUsersPage() {
  const { users, total, isLoading, error, offset, limit, setOffset, refetch } =
    useUsers();
  const {
    createUser,
    isLoading: isCreating,
    error: createError,
  } = useCreateUser();
  const {
    updateUser,
    isLoading: isUpdating,
    error: updateError,
  } = useUpdateUser();
  const { deactivateUser, isLoading: isDeactivating } = useDeactivateUser();
  const { activateUser, isLoading: isActivating } = useActivateUser();

  const [editingUser, setEditingUser] = useState<User | null>(null);

  const handleCreate = async (payload: Parameters<typeof createUser>[0]) => {
    const result = await createUser(payload);
    if (result) {
      await refetch();
    }
    return result;
  };

  const handleUpdate = async (
    userId: string,
    payload: Parameters<typeof updateUser>[1],
  ) => {
    const result = await updateUser(userId, payload);
    if (result) {
      await refetch();
    }
    return result;
  };

  const handleToggleActive = async (user: User) => {
    if (user.is_active) {
      await deactivateUser(user.id);
    } else {
      await activateUser(user.id);
    }
    await refetch();
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div>
      <h1 className="mb-1 text-xl font-medium text-foreground">ユーザー管理</h1>
      <p className="mb-5 text-sm text-text-subtle">
        ユーザーの追加・編集・無効化を管理します
      </p>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>ユーザー追加</CardTitle>
        </CardHeader>
        <CardContent>
          <CreateUserForm
            onSubmit={handleCreate}
            isLoading={isCreating}
            error={createError}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>ユーザー一覧</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="py-8 text-center text-sm text-text-muted">
              読み込み中...
            </p>
          ) : error ? (
            <p className="py-8 text-center text-sm text-danger-text">
              ユーザー一覧の取得に失敗しました ({error.status})
            </p>
          ) : (
            <>
              <UserTable
                users={users}
                onEdit={setEditingUser}
                onToggleActive={handleToggleActive}
                isToggling={isDeactivating || isActivating}
              />
              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm text-text-subtle">
                    {total} 件中 {offset + 1} -{" "}
                    {Math.min(offset + limit, total)} 件を表示
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={currentPage <= 1}
                      onClick={() => setOffset(offset - limit)}
                    >
                      前へ
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={currentPage >= totalPages}
                      onClick={() => setOffset(offset + limit)}
                    >
                      次へ
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {editingUser && (
        <EditUserModal
          user={editingUser}
          onSubmit={handleUpdate}
          onClose={() => setEditingUser(null)}
          isLoading={isUpdating}
          error={updateError}
        />
      )}
    </div>
  );
}
