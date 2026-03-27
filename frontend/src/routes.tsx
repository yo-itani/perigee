import { createBrowserRouter } from "react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { AdminGuard } from "@/components/guards/AdminGuard";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { SchedulingPage } from "@/features/scheduling/pages/SchedulingPage";
import { PreparationPage } from "@/features/preparation/pages/PreparationPage";
import { RecordingPage } from "@/features/recording/pages/RecordingPage";
import { PublishingPage } from "@/features/publishing/pages/PublishingPage";
import { RecordViewerPage } from "@/features/record-viewer/pages/RecordViewerPage";
import { RecordListPage } from "@/features/record-viewer/pages/RecordListPage";
import { ScheduleListPage } from "@/features/preparation/pages/ScheduleListPage";
import { RecordingListPage } from "@/features/recording/pages/RecordingListPage";
import { DraftListPage } from "@/features/publishing/pages/DraftListPage";
import { NotificationSettingPage } from "@/features/notification-settings/pages/NotificationSettingPage";
import { SetupPage } from "@/features/setup/pages/SetupPage";
import { SetupGuard } from "@/features/setup/components/SetupGuard";
import { AdminUsersPage } from "@/features/admin/pages/AdminUsersPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export const router = createBrowserRouter([
  { path: "setup", element: <SetupPage /> },
  {
    element: <SetupGuard />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "scheduling", element: <SchedulingPage /> },
          { path: "schedules", element: <ScheduleListPage /> },
          {
            path: "schedules/:scheduleId/preparation",
            element: <PreparationPage />,
          },
          { path: "records/in-progress", element: <RecordingListPage /> },
          { path: "records/drafts", element: <DraftListPage /> },
          { path: "records/:recordId/recording", element: <RecordingPage /> },
          { path: "records/:recordId/publish", element: <PublishingPage /> },
          { path: "records", element: <RecordListPage /> },
          { path: "records/:recordId", element: <RecordViewerPage /> },
          {
            path: "settings/notifications",
            element: <NotificationSettingPage />,
          },
          {
            path: "admin/users",
            element: (
              <AdminGuard>
                <AdminUsersPage />
              </AdminGuard>
            ),
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
