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
    <aside className="flex h-full w-[220px] flex-col border-r border-border-subtle bg-background overflow-y-auto px-4 pt-6">
      <div className="mb-5 border-b border-border-subtle pb-2.5">
        <span className="text-[13px] font-medium text-foreground">perigee</span>
      </div>
      <nav>
        {navGroups.map((group) => (
          <div key={group.label} className="mb-5">
            <div className="mb-1.5 text-[11px] tracking-[0.05em] text-text-muted">
              {group.label}
            </div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `block rounded-lg px-2.5 py-[7px] text-[13px] transition-colors duration-100 ${
                    isActive
                      ? "bg-surface-secondary font-medium text-foreground"
                      : "text-text-subtle hover:bg-surface-secondary hover:text-foreground"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
