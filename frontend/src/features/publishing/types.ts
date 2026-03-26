/**
 * Shared type definitions for the publishing feature.
 *
 * These types mirror the backend API response schemas for the publishing flow.
 */

export interface SuggestedViewersResponse {
  suggested_viewer_ids: string[];
}

export interface SetViewersResponse {
  record_id: string;
}

export interface PublishRecordResponse {
  record_id: string;
}
