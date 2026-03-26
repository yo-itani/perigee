/**
 * Shared type definitions for the dashboard feature.
 *
 * These types mirror the backend API response schemas and are shared
 * across hooks and components.
 */

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

export interface PendingActionItem {
  action_item_id: string;
  content: string;
  created_at: string;
  record_id: string;
  counterpart_id: string;
  conducted_at: string;
}

export interface PendingActionItemsResponse {
  items: PendingActionItem[];
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
