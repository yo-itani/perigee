/**
 * Shared type definitions for action items.
 *
 * These types mirror the backend API response schemas:
 * - PendingActionItemSchema (per-counterpart endpoint: GET /action-items/pending/{counterpart_id})
 * - AllPendingActionItemSchema (all-counterpart endpoint: GET /action-items/pending)
 */

/**
 * A pending action item for a specific counterpart.
 * Matches backend PendingActionItemSchema which includes organizer_id.
 * Used in the preparation page (per-counterpart context).
 */
export interface PendingActionItem {
  action_item_id: string;
  content: string;
  created_at: string;
  record_id: string;
  organizer_id: string;
  conducted_at: string;
}

/**
 * A pending action item across all counterparts.
 * Matches backend AllPendingActionItemSchema which includes counterpart_id.
 * Used in the dashboard page (all-counterpart overview).
 */
export interface AllPendingActionItem {
  action_item_id: string;
  content: string;
  created_at: string;
  record_id: string;
  counterpart_id: string;
  conducted_at: string;
}

/**
 * Response for GET /action-items/pending/{counterpart_id}.
 */
export interface PendingActionItemsResponse {
  items: PendingActionItem[];
}

/**
 * Response for GET /action-items/pending.
 */
export interface AllPendingActionItemsResponse {
  items: AllPendingActionItem[];
}
