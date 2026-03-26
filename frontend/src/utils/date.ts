/**
 * Shared date formatting utilities.
 * Separated from feature-specific files to avoid duplication and
 * ensure consistent behavior across the application.
 */

/**
 * Return a relative label like "今日", "明日", "2日後", "昨日", "3日前".
 */
export function getRelativeLabel(isoString: string): string {
  const now = new Date();
  const target = new Date(isoString);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const targetStart = new Date(
    target.getFullYear(),
    target.getMonth(),
    target.getDate(),
  );
  const diffMs = targetStart.getTime() - todayStart.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "今日";
  if (diffDays === 1) return "明日";
  if (diffDays > 1) return `${diffDays}日後`;
  if (diffDays === -1) return "昨日";
  return `${Math.abs(diffDays)}日前`;
}

/**
 * Format an ISO datetime string to a localized Japanese date string.
 * e.g. "2026年4月3日（金）"
 */
export function formatDateJa(isoString: string): string {
  const date = new Date(isoString);
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const weekday = weekdays[date.getDay()];
  return `${year}年${month}月${day}日（${weekday}）`;
}

/**
 * Format an ISO datetime string to time "HH:MM".
 */
export function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return `${date.getHours()}:${String(date.getMinutes()).padStart(2, "0")}`;
}

/**
 * Format an ISO datetime string to a full date-time string.
 * e.g. "2026/04/03（金）10:00"
 */
export function formatScheduleDateTime(isoString: string): string {
  const date = new Date(isoString);
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const weekday = weekdays[date.getDay()];
  const hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}/${month}/${day}（${weekday}）${hours}:${minutes}`;
}

/**
 * Format an ISO datetime string to a short date string.
 * e.g. "2026/03/20"
 */
export function formatDateShort(isoString: string): string {
  const date = new Date(isoString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}/${month}/${day}`;
}

/**
 * Format an ISO datetime string to a Japanese comment date.
 * e.g. "3月31日"
 */
export function formatCommentDate(isoString: string): string {
  const date = new Date(isoString);
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}
