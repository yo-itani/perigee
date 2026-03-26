import { useNavigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import { useScheduleDetail } from "../hooks/useScheduleDetail";
import { useScheduleAgendas } from "../hooks/useScheduleAgendas";
import { useAddAgenda } from "../hooks/useAddAgenda";
import { useDeleteAgenda } from "../hooks/useDeleteAgenda";
import { useAddAgendaComment } from "../hooks/useAddAgendaComment";
import { usePendingActionItems } from "../hooks/usePendingActionItems";
import { useStartSession } from "../hooks/useStartSession";
import { ScheduleInfoCard } from "../components/ScheduleInfoCard";
import { AgendaList } from "../components/AgendaList";
import { PendingActionItemList } from "../components/PendingActionItemList";
import { getRelativeLabel } from "../utils";

export function PreparationPage() {
  const { scheduleId } = useParams<{ scheduleId: string }>();
  const navigate = useNavigate();

  const {
    schedule,
    isLoading: scheduleLoading,
    error: scheduleError,
  } = useScheduleDetail(scheduleId!);

  const {
    agendas,
    isLoading: agendasLoading,
    error: agendasError,
    refetch: refetchAgendas,
  } = useScheduleAgendas(scheduleId!);

  const { addAgenda, isSubmitting: isAddingAgenda } = useAddAgenda(scheduleId!);

  const { deleteAgenda } = useDeleteAgenda(scheduleId!);

  const { addComment, isSubmitting: isAddingComment } = useAddAgendaComment();

  const {
    startSession,
    isSubmitting: isStarting,
    error: startError,
  } = useStartSession();

  // Determine counterpart_id from schedule for pending action items
  const counterpartId = schedule?.counterpart_id ?? null;

  const {
    items: pendingItems,
    isLoading: pendingLoading,
    error: pendingError,
  } = usePendingActionItems(counterpartId);

  const handleAddAgenda = async (topic: string) => {
    const result = await addAgenda(topic);
    if (result) {
      refetchAgendas();
    }
  };

  const handleDeleteAgenda = async (agendaId: string) => {
    const success = await deleteAgenda(agendaId);
    if (success) {
      refetchAgendas();
    }
  };

  const handleAddComment = async (agendaId: string, body: string) => {
    const result = await addComment(agendaId, body);
    if (result) {
      refetchAgendas();
    }
  };

  const handleAddToAgenda = (content: string) => {
    void handleAddAgenda(content);
  };

  const handleStartSession = async () => {
    if (!scheduleId || !schedule) return;
    const conductedAt = new Date().toISOString();
    const result = await startSession(scheduleId, conductedAt);
    if (result) {
      void navigate(`/records/${result.record_id}/recording`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            {schedule?.title ?? "準備画面"}
          </h1>
          {schedule && (
            <p className="mt-1 text-muted-foreground">
              {getRelativeLabel(schedule.scheduled_at)}
            </p>
          )}
        </div>
      </div>

      {/* Schedule info */}
      <ScheduleInfoCard
        schedule={schedule}
        isLoading={scheduleLoading}
        error={scheduleError}
      />

      {/* Agenda list */}
      <AgendaList
        agendas={agendas}
        isLoading={agendasLoading}
        error={agendasError}
        onAddAgenda={handleAddAgenda}
        onDeleteAgenda={handleDeleteAgenda}
        onAddComment={handleAddComment}
        isAddingAgenda={isAddingAgenda}
        isAddingComment={isAddingComment}
      />

      {/* Pending action items */}
      <PendingActionItemList
        items={pendingItems}
        isLoading={pendingLoading}
        error={pendingError}
        onAddToAgenda={handleAddToAgenda}
      />

      {/* Start session */}
      <div className="flex justify-end">
        {startError && (
          <p className="mr-4 self-center text-sm text-destructive">
            {startError}
          </p>
        )}
        <Button
          size="lg"
          onClick={() => void handleStartSession()}
          disabled={isStarting || scheduleLoading}
        >
          {isStarting ? "開始中..." : "1on1 を開始する"}
        </Button>
      </div>
    </div>
  );
}
