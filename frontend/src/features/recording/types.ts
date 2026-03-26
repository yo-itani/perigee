/**
 * Shared type definitions for the recording feature.
 *
 * These types mirror the backend API response schemas for the Record context.
 */

export interface RecordActionItem {
  action_item_id: string;
  title: string;
  is_completed: boolean;
  counterpart_id: string;
  created_at: string;
  /** TODO: API未対応。バックエンドにdue_dateフィールドが追加されたら連携する */
  due_date?: string;
}

export interface RecordDetail {
  record_id: string;
  organizer_id: string;
  counterpart_id: string;
  schedule_id: string | null;
  memo: string;
  status: string;
  confirmed_agenda_ids: string[];
  action_items: RecordActionItem[];
  conducted_at: string;
  created_at: string;
  updated_at: string;
}

export interface ConfirmAgendaResponse {
  record_id: string;
  agenda_id: string;
}

export interface AddActionItemResponse {
  action_item_id: string;
}
