/**
 * Shared type definitions for the notification-settings feature.
 *
 * These types mirror the backend API response schemas (NotificationSettingResponse)
 * and request schemas (UpdateNotificationSettingRequest).
 */

export interface NotificationSetting {
  user_id: string;
  reminder_minutes_before: number;
  is_enabled: boolean;
}

export interface UpdateNotificationSettingPayload {
  reminder_minutes_before: number;
  is_enabled: boolean;
}
