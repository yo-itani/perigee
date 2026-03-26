import { Outlet } from "react-router";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppLayout() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden bg-surface">
        <Header />
        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-[680px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
