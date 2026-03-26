/**
 * Shared type definitions for the record-viewer feature.
 *
 * These types mirror the backend API response schemas and are shared
 * across hooks and components.
 */

// -- Record detail (GET /records/{id}) ----------------------------------------

export interface RecordActionItem {
  action_item_id: string;
  title: string;
  is_completed: boolean;
  counterpart_id: string;
  created_at: string;
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

// -- Comments (GET /records/{id}/comments) ------------------------------------

export interface RecordComment {
  comment_id: string;
  author_id: string;
  body: string;
  created_at: string;
}

export interface ListRecordCommentsResponse {
  comments: RecordComment[];
}

// -- Viewers (GET /records/{id}/viewers) --------------------------------------

export interface GetViewersResponse {
  viewer_ids: string[];
}

// -- Add comment (POST /records/{id}/comments) --------------------------------

export interface AddRecordCommentResponse {
  comment_id: string;
}

// -- Complete action item (POST /action-items/{id}/complete) ------------------

export interface CompleteActionItemResponse {
  action_item_id: string;
}

// -- User role ----------------------------------------------------------------

export type RecordViewerRole = "organizer" | "counterpart" | "viewer";
