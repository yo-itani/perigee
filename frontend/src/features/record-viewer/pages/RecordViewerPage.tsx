import { useNavigate, useParams } from "react-router";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useRecordDetail } from "../hooks/useRecordDetail";
import { useRecordComments } from "../hooks/useRecordComments";
import { useRecordViewers } from "../hooks/useRecordViewers";
import { useAddRecordComment } from "../hooks/useAddRecordComment";
import { useCompleteActionItem } from "../hooks/useCompleteActionItem";
import { RecordInfoCard } from "../components/RecordInfoCard";
import { RecordAgendaList } from "../components/RecordAgendaList";
import { RecordMemo } from "../components/RecordMemo";
import { RecordActionItems } from "../components/RecordActionItems";
import { ViewerList } from "../components/ViewerList";
import { RecordCommentSection } from "../components/RecordCommentSection";
import { determineRole } from "../utils";

export function RecordViewerPage() {
  const { recordId } = useParams<{ recordId: string }>();
  const navigate = useNavigate();
  const { userId } = useCurrentUser();

  const {
    record,
    isLoading: recordLoading,
    error: recordError,
    refetch: refetchRecord,
  } = useRecordDetail(recordId!);

  const {
    comments,
    isLoading: commentsLoading,
    error: commentsError,
    refetch: refetchComments,
  } = useRecordComments(recordId!);

  const {
    viewerIds,
    isLoading: viewersLoading,
    error: viewersError,
  } = useRecordViewers(recordId!);

  const {
    addComment,
    isSubmitting: isAddingComment,
    error: addCommentError,
  } = useAddRecordComment(recordId!);

  const {
    completeItem,
    isSubmitting: isCompleting,
    error: completeError,
  } = useCompleteActionItem();

  const role = record
    ? determineRole(userId, record.organizer_id, record.counterpart_id)
    : "viewer";

  const handleAddComment = async (body: string): Promise<boolean> => {
    const result = await addComment(body);
    if (result) {
      refetchComments();
      return true;
    }
    return false;
  };

  const handleCompleteActionItem = async (actionItemId: string) => {
    const result = await completeItem(actionItemId);
    if (result) {
      refetchRecord();
    }
  };

  const handleEdit = () => {
    if (recordId) {
      void navigate(`/records/${recordId}/recording`);
    }
  };

  const handleChangeViewers = () => {
    if (recordId) {
      void navigate(`/records/${recordId}/publish`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">
          {record ? `記録 - ${record.record_id}` : "記録閲覧"}
        </h1>
        {record && (
          <p className="mt-1 text-muted-foreground">
            {record.status === "published" ? "公開済み" : record.status}
          </p>
        )}
      </div>

      {/* Basic info */}
      <RecordInfoCard
        record={record}
        role={role}
        isLoading={recordLoading}
        error={recordError}
        onEdit={handleEdit}
      />

      {/* Agenda list */}
      <RecordAgendaList
        confirmedAgendaIds={record?.confirmed_agenda_ids ?? []}
        isLoading={recordLoading}
      />

      {/* Memo */}
      <RecordMemo memo={record?.memo ?? ""} isLoading={recordLoading} />

      {/* Action items */}
      <RecordActionItems
        actionItems={record?.action_items ?? []}
        isLoading={recordLoading}
        role={role}
        onComplete={(id) => void handleCompleteActionItem(id)}
        isCompleting={isCompleting}
        completeError={completeError}
      />

      {/* Viewers */}
      <ViewerList
        viewerIds={viewerIds}
        currentUserId={userId}
        counterpartId={record?.counterpart_id ?? ""}
        role={role}
        isLoading={viewersLoading}
        error={viewersError}
        onChangeViewers={handleChangeViewers}
      />

      {/* Comments */}
      <RecordCommentSection
        comments={comments}
        isLoading={commentsLoading}
        error={commentsError}
        onAddComment={handleAddComment}
        isSubmitting={isAddingComment}
        addCommentError={addCommentError}
      />
    </div>
  );
}
