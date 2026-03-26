/**
 * Shared type definitions for the dashboard feature.
 *
 * These types mirror the backend API response schemas and are shared
 * across hooks and components.
 */

// Re-export shared action item types for use within this feature.
// Dashboard uses AllPendingActionItem (all-counterpart endpoint) but
// aliases it as PendingActionItem for backward compatibility within this feature.
export type {
  AllPendingActionItem as PendingActionItem,
  AllPendingActionItemsResponse as PendingActionItemsResponse,
} from "@/types/action-item";

export interface UpcomingScheduleItem {
  schedule_id: string;
  organizer_id: string;
  counterpart_id: string;
  scheduled_at: string;
  status: string;
  title: string;
  schedule_group_id: string | null;
}

export interface UpcomingSchedulesResponse {
  schedules: UpcomingScheduleItem[];
}

export interface DraftRecordItem {
  record_id: string;
  counterpart_id: string;
  conducted_at: string;
  memo_excerpt: string;
  created_at: string;
  schedule_id: string | null;
}

export interface DraftRecordsResponse {
  items: DraftRecordItem[];
}

export interface NotificationRecord {
  id: string;
  recipient_id: string;
  notification_type: string;
  title: string;
  body: string;
  link: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: NotificationRecord[];
}
