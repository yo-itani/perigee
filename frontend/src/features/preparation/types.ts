/**
 * Shared type definitions for the preparation feature.
 *
 * These types mirror the backend API response schemas and are shared
 * across hooks and components.
 */

// Re-export shared action item types for use within this feature
export type {
  PendingActionItem,
  PendingActionItemsResponse,
} from "@/types/action-item";

export interface ScheduleDetail {
  schedule_id: string;
  organizer_id: string;
  counterpart_id: string;
  title: string;
  scheduled_at: string;
  status: string;
  schedule_group_id: string | null;
  created_at: string;
  updated_at: string;
  // TODO: Backend GET /schedules/{id} (GetScheduleDetailResponse) does not yet
  // include duration_minutes or recurrence. Add these fields to the backend
  // schema when the domain model supports them.
  duration_minutes?: number;
  recurrence?: string;
}

export interface AgendaComment {
  comment_id: string;
  author_id: string;
  body: string;
  created_at: string;
}

export interface AgendaItem {
  agenda_id: string;
  topic: string;
  added_by: string;
  added_by_tag: string;
  comments: AgendaComment[];
  created_at: string;
}

export interface AgendasResponse {
  agendas: AgendaItem[];
}

export interface AddAgendaResponse {
  agenda_id: string;
}

export interface AddAgendaCommentResponse {
  comment_id: string;
}

export interface StartSessionResponse {
  record_id: string;
}
