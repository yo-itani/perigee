import { useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import { useRecordDetail } from "@/features/recording/hooks/useRecordDetail";
import { useUpdateMemo } from "@/hooks/useUpdateMemo";
import { useSaveDraft } from "@/hooks/useSaveDraft";
import { useSuggestedViewers } from "../hooks/useSuggestedViewers";
import { useSetViewers } from "../hooks/useSetViewers";
import { usePublishRecord } from "../hooks/usePublishRecord";
import { MemoEditor } from "../components/MemoEditor";
import { ActionItemSummary } from "../components/ActionItemSummary";
import { ViewerSelectModal } from "../components/ViewerSelectModal";
import { formatScheduleDateTime, getStatusLabel } from "../utils";

export function PublishingPage() {
  const { recordId } = useParams<{ recordId: string }>();
  const navigate = useNavigate();

  const {
    record,
    isLoading: recordLoading,
    error: recordError,
  } = useRecordDetail(recordId!);

  const {
    suggestedViewerIds,
    isLoading: suggestedViewersLoading,
    error: suggestedViewersError,
  } = useSuggestedViewers(recordId!);

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

  const {
    setViewers,
    isSubmitting: isSettingViewers,
    error: setViewersError,
  } = useSetViewers(recordId!);

  const {
    publishRecord,
    isSubmitting: isPublishing,
    error: publishError,
  } = usePublishRecord(recordId!);

  const [memo, setMemo] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const savingInProgressRef = useRef(false);

  // Initialize memo from record once loaded
  const currentMemo = memo ?? record?.memo ?? "";

  const handleMemoChange = (value: string) => {
    setMemo(value);
  };

  const handleSaveMemo = () => {
    // Defer to next frame so button click handlers can set savingInProgressRef first
    setTimeout(() => {
      if (savingInProgressRef.current) return;
      void updateMemo(currentMemo);
    }, 0);
  };

  const handleSaveDraft = async () => {
    savingInProgressRef.current = true;
    try {
      const memoResult = await updateMemo(currentMemo);
      if (!memoResult) return;
      await saveDraft();
    } finally {
      savingInProgressRef.current = false;
    }
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handlePublish = async (viewerIds: string[]) => {
    savingInProgressRef.current = true;
    try {
      const memoResult = await updateMemo(currentMemo);
      if (!memoResult) return;

      const viewersResult = await setViewers(viewerIds);
      if (!viewersResult) return;

      const result = await publishRecord();
      if (result) {
        setIsModalOpen(false);
        void navigate(`/records/${recordId}`);
      }
    } finally {
      savingInProgressRef.current = false;
    }
  };

  const handleModalSaveDraft = async (viewerIds: string[]) => {
    savingInProgressRef.current = true;
    try {
      const memoResult = await updateMemo(currentMemo);
      if (!memoResult) return;

      const viewersResult = await setViewers(viewerIds);
      if (!viewersResult) return;

      const result = await saveDraft();
      if (result) {
        setIsModalOpen(false);
        void navigate(`/records/drafts`);
      }
    } finally {
      savingInProgressRef.current = false;
    }
  };

  // Show loading state
  if (recordLoading || suggestedViewersLoading) {
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

  if (suggestedViewersError) {
    return (
      <div className="space-y-6">
        <p className="text-sm text-destructive" role="alert">
          {suggestedViewersError}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">公開フロー</h1>
          {record && (
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              {getStatusLabel(record.status)}
            </span>
          )}
        </div>
        {record && (
          <p className="mt-1 text-muted-foreground">
            {formatScheduleDateTime(record.conducted_at)}
          </p>
        )}
      </div>

      {/* Status bar */}
      <div className="flex items-center gap-2 rounded-lg bg-green-50 px-4 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200">
        <div className="h-2 w-2 rounded-full bg-green-500" />
        1on1 完了・記録を編集中
      </div>

      {/* Memo editor */}
      <MemoEditor
        memo={currentMemo}
        onMemoChange={handleMemoChange}
        onSaveMemo={() => void handleSaveMemo()}
        isSaving={isSavingMemo}
        error={memoError}
      />

      {/* Action items (read-only) */}
      <ActionItemSummary actionItems={record?.action_items ?? []} />

      {/* Footer */}
      <div className="flex justify-end gap-3">
        {saveDraftError && (
          <p className="self-center text-sm text-destructive">
            {saveDraftError}
          </p>
        )}
        {setViewersError && (
          <p className="self-center text-sm text-destructive">
            {setViewersError}
          </p>
        )}
        <Button
          variant="ghost"
          onClick={() => void handleSaveDraft()}
          disabled={isSavingDraft || isSavingMemo}
        >
          {isSavingDraft ? "保存中..." : "下書き保存"}
        </Button>
        <Button
          onClick={handleOpenModal}
          disabled={isSavingDraft || isSavingMemo}
        >
          公開設定へ
        </Button>
      </div>

      {/* Viewer select modal */}
      <ViewerSelectModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        suggestedViewerIds={suggestedViewerIds}
        counterpartId={record?.counterpart_id ?? ""}
        onPublish={(viewerIds) => void handlePublish(viewerIds)}
        onSaveDraft={(viewerIds) => void handleModalSaveDraft(viewerIds)}
        isPublishing={isPublishing || isSettingViewers}
        isSavingDraft={isSavingDraft || isSettingViewers}
        publishError={publishError}
        saveDraftError={saveDraftError}
      />
    </div>
  );
}
