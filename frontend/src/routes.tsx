import { createBrowserRouter } from "react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { SchedulingPage } from "@/features/scheduling/pages/SchedulingPage";
import { PreparationPage } from "@/features/preparation/pages/PreparationPage";
import { RecordingPage } from "@/features/recording/pages/RecordingPage";
import { PublishingPage } from "@/features/publishing/pages/PublishingPage";
import { RecordViewerPage } from "@/features/record-viewer/pages/RecordViewerPage";
import { NotificationSettingPage } from "@/features/notification-settings/pages/NotificationSettingPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "scheduling", element: <SchedulingPage /> },
      {
        path: "schedules/:scheduleId/preparation",
        element: <PreparationPage />,
      },
      { path: "records/:recordId/recording", element: <RecordingPage /> },
      { path: "records/:recordId/publish", element: <PublishingPage /> },
      { path: "records/:recordId", element: <RecordViewerPage /> },
      { path: "settings/notifications", element: <NotificationSettingPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
