import { useState } from "react";
import {
  ScheduleGroupForm,
  type ScheduleGroupFormData,
} from "../components/ScheduleGroupForm";
import {
  ConsultationRequestForm,
  type ConsultationRequestFormData,
} from "../components/ConsultationRequestForm";
import { useCreateScheduleGroup } from "../hooks/useCreateScheduleGroup";
import { useSendConsultationRequest } from "../hooks/useSendConsultationRequest";

type TabId = "regular" | "adhoc";

export function SchedulingPage() {
  const [activeTab, setActiveTab] = useState<TabId>("regular");

  const {
    createScheduleGroup,
    isLoading: isCreatingGroup,
    error: createGroupError,
  } = useCreateScheduleGroup();

  const {
    sendConsultationRequest,
    isLoading: isSendingRequest,
    error: sendRequestError,
  } = useSendConsultationRequest();

  const handleScheduleGroupSubmit = async (data: ScheduleGroupFormData) => {
    await createScheduleGroup({
      title: data.title,
      counterpart_schedules: data.counterpartSchedules.map((cp) => ({
        counterpart_id: cp.counterpartId,
        scheduled_at: new Date(
          `${cp.startDate}T${cp.startTime}:00`,
        ).toISOString(),
      })),
      agenda_topics:
        data.agendaTopics.length > 0 ? data.agendaTopics : undefined,
    });
  };

  const handleConsultationSubmit = async (
    data: ConsultationRequestFormData,
  ) => {
    const agendaTopics = data.agendaText
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    await sendConsultationRequest({
      organizer_id: data.organizerId,
      scheduled_at: new Date(data.scheduledAt).toISOString(),
      title: data.title,
      agenda_topics: agendaTopics,
    });
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 text-2xl font-bold">1on1 を設定する</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        定期スケジュールまたはアドホック相談を設定します
      </p>

      <div className="mb-6 flex gap-1 rounded-lg border border-border p-1">
        <button
          type="button"
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "regular"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted"
          }`}
          onClick={() => setActiveTab("regular")}
        >
          定期スケジュール型
        </button>
        <button
          type="button"
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "adhoc"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted"
          }`}
          onClick={() => setActiveTab("adhoc")}
        >
          アドホック相談型
        </button>
      </div>

      {activeTab === "regular" && (
        <ScheduleGroupForm
          onSubmit={handleScheduleGroupSubmit}
          isSubmitting={isCreatingGroup}
          submitError={createGroupError}
        />
      )}

      {activeTab === "adhoc" && (
        <ConsultationRequestForm
          onSubmit={handleConsultationSubmit}
          isSubmitting={isSendingRequest}
          submitError={sendRequestError}
        />
      )}
    </div>
  );
}
