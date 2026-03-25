import { useCurrentUser } from "@/hooks/useCurrentUser";

export function Header() {
  const { name } = useCurrentUser();

  return (
    <header className="flex h-14 items-center border-b border-border px-6">
      <div className="ml-auto flex items-center gap-2">
        <span className="text-sm text-muted-foreground">{name}</span>
      </div>
    </header>
  );
}
