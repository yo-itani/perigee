/**
 * Utility constants and functions for the notification-settings feature.
 * Separated from components to avoid react-refresh warnings.
 */

export const MIN_REMINDER_MINUTES = 5;
export const MAX_REMINDER_MINUTES = 1440;

/**
 * Validate that the reminder minutes value is within the allowed range.
 * Returns an error message if invalid, or null if valid.
 */
export function validateReminderMinutes(value: number): string | null {
  if (!Number.isInteger(value)) {
    return "リマインド時間は整数で入力してください";
  }
  if (value < MIN_REMINDER_MINUTES || value > MAX_REMINDER_MINUTES) {
    return `リマインド時間は${MIN_REMINDER_MINUTES}分から${MAX_REMINDER_MINUTES}分の間で設定してください`;
  }
  return null;
}
