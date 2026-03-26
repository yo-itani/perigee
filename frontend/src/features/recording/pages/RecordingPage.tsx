import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import { useScheduleAgendas } from "@/features/preparation/hooks/useScheduleAgendas";
import { useAddAgenda } from "@/features/preparation/hooks/useAddAgenda";
import { useRecordDetail } from "../hooks/useRecordDetail";
import { useConfirmAgenda } from "../hooks/useConfirmAgenda";
import { useAddActionItem } from "../hooks/useAddActionItem";
import { useDeleteActionItem } from "../hooks/useDeleteActionItem";
import { useUpdateMemo } from "@/hooks/useUpdateMemo";
import { useSaveDraft } from "@/hooks/useSaveDraft";
import { AgendaChecklist } from "../components/AgendaChecklist";
import { MemoEditor } from "../components/MemoEditor";
import { ActionItemForm } from "../components/ActionItemForm";
import { formatScheduleDateTime } from "../utils";

export function RecordingPage() {
  const { recordId } = useParams<{ recordId: string }>();
  const navigate = useNavigate();

  const {
    record,
    isLoading: recordLoading,
    error: recordError,
    refetch: refetchRecord,
  } = useRecordDetail(recordId!);

  // Load agendas from the linked schedule
  const scheduleId = record?.schedule_id ?? null;
  const {
    agendas,
    isLoading: agendasLoading,
    error: agendasError,
    refetch: refetchAgendas,
  } = useScheduleAgendas(scheduleId ?? "");

  const {
    addAgenda,
    isSubmitting: isAddingAgenda,
    error: addAgendaError,
  } = useAddAgenda(scheduleId ?? "");

  const { confirmAgenda, error: confirmAgendaError } = useConfirmAgenda(
    recordId!,
  );

  const {
    addActionItem,
    isSubmitting: isAddingActionItem,
    error: addActionItemError,
  } = useAddActionItem(recordId!);

  const { deleteActionItem, error: deleteActionItemError } =
    useDeleteActionItem(recordId!);

  const {
    updateMemo,
    isSubmitting: isSavingMemo,
    error: memoError,
  } = useUpdateMemo(recordId!);

  const {
    saveDraft,
    isSubmitting: isSavingDraft,
    error: saveDraftError,
  } = useSaveDraft(recordId!);

  const [memo, setMemo] = useState<string | null>(null);

  // Initialize memo from record once loaded
  const currentMemo = memo ?? record?.memo ?? "";

  const handleMemoChange = (value: string) => {
    setMemo(value);
  };

  const handleSaveMemo = async () => {
    await updateMemo(currentMemo);
  };

  const handleConfirmAgenda = async (agendaId: string) => {
    const result = await confirmAgenda(agendaId);
    if (result) {
      refetchRecord();
    }
  };

  const handleAddAgenda = async (topic: string): Promise<boolean> => {
    const result = await addAgenda(topic);
    if (result) {
      refetchAgendas();
      return true;
    }
    return false;
  };

  const handleAddActionItem = async (title: string): Promise<boolean> => {
    const result = await addActionItem(title);
    if (result) {
      refetchRecord();
      return true;
    }
    return false;
  };

  const handleDeleteActionItem = async (actionItemId: string) => {
    const success = await deleteActionItem(actionItemId);
    if (success) {
      refetchRecord();
    }
  };

  const handleSaveAndComplete = async () => {
    // Save memo first, then save draft, then navigate to publish
    await updateMemo(currentMemo);
    const result = await saveDraft();
    if (result) {
      void navigate(`/records/${recordId}/publish`);
    }
  };

  // Show loading state
  if (recordLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 rounded bg-muted" />
          <div className="h-4 w-40 rounded bg-muted" />
        </div>
      </div>
    );
  }

  // Show error state
  if (recordError) {
    return (
      <div className="space-y-6">
        <p className="text-sm text-destructive" role="alert">
          {recordError}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">1on1 記録</h1>
          {record && (
            <p className="mt-1 text-muted-foreground">
              {formatScheduleDateTime(record.conducted_at)}
            </p>
          )}
        </div>
        <Button
          size="lg"
          onClick={() => void handleSaveAndComplete()}
          disabled={isSavingDraft || isSavingMemo}
        >
          {isSavingDraft ? "保存中..." : "完了として保存"}
        </Button>
      </div>

      {/* Status bar */}
      <div className="flex items-center gap-2 rounded-lg bg-green-50 px-4 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200">
        <div className="h-2 w-2 rounded-full bg-green-500" />
        実施中
      </div>

      {/* Agenda checklist */}
      {scheduleId && (
        <AgendaChecklist
          agendas={agendas}
          confirmedAgendaIds={record?.confirmed_agenda_ids ?? []}
          isLoading={agendasLoading}
          error={agendasError}
          onConfirmAgenda={handleConfirmAgenda}
          onAddAgenda={handleAddAgenda}
          isAddingAgenda={isAddingAgenda}
          confirmError={confirmAgendaError}
          addAgendaError={addAgendaError}
        />
      )}

      {/* Memo editor */}
      <MemoEditor
        memo={currentMemo}
        onMemoChange={handleMemoChange}
        onSaveMemo={() => void handleSaveMemo()}
        isSaving={isSavingMemo}
        error={memoError}
      />

      {/* Action items */}
      <ActionItemForm
        actionItems={record?.action_items ?? []}
        onAddActionItem={handleAddActionItem}
        onDeleteActionItem={handleDeleteActionItem}
        isAdding={isAddingActionItem}
        addError={addActionItemError}
        deleteError={deleteActionItemError}
      />

      {/* Footer save button */}
      <div className="flex justify-end gap-3">
        {saveDraftError && (
          <p className="self-center text-sm text-destructive">
            {saveDraftError}
          </p>
        )}
        <Button
          size="lg"
          onClick={() => void handleSaveAndComplete()}
          disabled={isSavingDraft || isSavingMemo}
        >
          {isSavingDraft ? "保存中..." : "完了として保存"}
        </Button>
      </div>
    </div>
  );
}
