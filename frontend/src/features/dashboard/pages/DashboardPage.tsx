import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useUpcomingSchedules } from "../hooks/useUpcomingSchedules";
import { useDraftRecords } from "../hooks/useDraftRecords";
import { usePendingActionItems } from "../hooks/usePendingActionItems";
import { useUnreadNotifications } from "../hooks/useUnreadNotifications";
import { NextSessionCard } from "../components/NextSessionCard";
import { MetricsCards } from "../components/MetricsCards";
import { UpcomingSessionList } from "../components/UpcomingSessionList";
import { DraftRecordList } from "../components/DraftRecordList";
import { PendingActionList } from "../components/PendingActionList";
import { UnreadRecordList } from "../components/UnreadRecordList";
import { countThisWeekSchedules, formatDateJa } from "../utils";

export function DashboardPage() {
  const { name: userName } = useCurrentUser();
  const {
    schedules,
    isLoading: schedulesLoading,
    error: schedulesError,
  } = useUpcomingSchedules();
  const {
    drafts,
    isLoading: draftsLoading,
    error: draftsError,
  } = useDraftRecords();
  const {
    items: pendingItems,
    isLoading: pendingLoading,
    error: pendingError,
  } = usePendingActionItems();
  const {
    notifications,
    isLoading: notificationsLoading,
    error: notificationsError,
  } = useUnreadNotifications();

  const today = formatDateJa(new Date().toISOString());
  const nextSchedule = schedules.length > 0 ? schedules[0] : null;

  // Metrics computed from existing API responses (per #148)
  const weeklyCount = countThisWeekSchedules(
    schedules.map((s) => s.scheduled_at),
  );
  const draftCount = drafts.length;
  // Note: overdue filtering requires a due_date field which is not yet
  // available in the pending action items API. For now, show total count.
  const overdueCount = 0;

  const metricsLoading = schedulesLoading || draftsLoading || pendingLoading;

  // Greeting sub-text
  const greetingSub = nextSchedule
    ? `${today}  今日は${nextSchedule.title}があります`
    : today;

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold">こんにちは、{userName}さん</h1>
        <p className="mt-1 text-muted-foreground">{greetingSub}</p>
      </div>

      {/* Next session card */}
      <NextSessionCard schedule={nextSchedule} isLoading={schedulesLoading} />

      {/* Metrics */}
      <MetricsCards
        weeklyCount={weeklyCount}
        draftCount={draftCount}
        overdueCount={overdueCount}
        isLoading={metricsLoading}
      />

      {/* Upcoming sessions */}
      <UpcomingSessionList
        schedules={schedules}
        isLoading={schedulesLoading}
        error={schedulesError}
      />

      {/* Draft records */}
      <DraftRecordList
        drafts={drafts}
        isLoading={draftsLoading}
        error={draftsError}
      />

      {/* Pending action items */}
      <PendingActionList
        items={pendingItems}
        isLoading={pendingLoading}
        error={pendingError}
      />

      {/* Unread notifications */}
      <UnreadRecordList
        notifications={notifications}
        isLoading={notificationsLoading}
        error={notificationsError}
      />
    </div>
  );
}
