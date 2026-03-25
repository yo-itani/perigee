import { NavLink } from "react-router";

interface NavItem {
  to: string;
  label: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "ダッシュボード",
    items: [{ to: "/", label: "ダッシュボード" }],
  },
  {
    label: "スケジューリング",
    items: [{ to: "/scheduling", label: "1on1 を設定する" }],
  },
  {
    label: "1on1 実施",
    items: [
      { to: "/schedules", label: "準備画面（1on1前）" },
      { to: "/records/in-progress", label: "実施・記録画面" },
      { to: "/records/drafts", label: "公開フロー" },
    ],
  },
  {
    label: "閲覧・コメント",
    items: [{ to: "/records", label: "記録閲覧・コメント" }],
  },
  {
    label: "設定",
    items: [{ to: "/settings/notifications", label: "通知設定" }],
  },
];

export function Sidebar() {
  return (
    <aside className="flex h-full w-60 flex-col border-r border-border bg-sidebar">
      <div className="flex h-14 items-center border-b border-sidebar-border px-4">
        <span className="text-lg font-bold text-sidebar-foreground">
          perigee
        </span>
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-3">
            <div className="mb-1 px-3 text-xs tracking-wider text-muted-foreground">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `block rounded-md px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                        : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
