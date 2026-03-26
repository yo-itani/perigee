/**
 * Shared type definitions for the preparation feature.
 *
 * These types mirror the backend API response schemas and are shared
 * across hooks and components.
 */

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

export interface PendingActionItem {
  action_item_id: string;
  content: string;
  created_at: string;
  record_id: string;
  organizer_id: string;
  conducted_at: string;
}

export interface PendingActionItemsResponse {
  items: PendingActionItem[];
}

export interface StartSessionResponse {
  record_id: string;
}
