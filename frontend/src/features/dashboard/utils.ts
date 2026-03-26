/**
 * Utility functions for the dashboard feature.
 * Separated from components to avoid react-refresh warnings.
 */

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
 * Return a relative label like "今日", "明日", "2日後", "7日後".
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
 * Count schedules within the current week (Monday to Sunday).
 */
export function countThisWeekSchedules(scheduledAts: string[]): number {
  const now = new Date();
  const dayOfWeek = now.getDay();
  // Monday = 1 in getDay(); adjust so Monday is start of week
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + mondayOffset,
  );
  const sunday = new Date(
    monday.getFullYear(),
    monday.getMonth(),
    monday.getDate() + 7,
  );

  return scheduledAts.filter((isoString) => {
    const d = new Date(isoString);
    return d >= monday && d < sunday;
  }).length;
}

/**
 * Calculate the number of days between two dates.
 */
export function daysBetween(isoString: string, referenceDate?: Date): number {
  const ref = referenceDate ?? new Date();
  const target = new Date(isoString);
  const refStart = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate());
  const targetStart = new Date(
    target.getFullYear(),
    target.getMonth(),
    target.getDate(),
  );
  const diffMs = refStart.getTime() - targetStart.getTime();
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

/**
 * Get the relative badge variant based on days until the schedule.
 */
export function getScheduleBadgeVariant(
  isoString: string,
): "success" | "warning" | "default" {
  const label = getRelativeLabel(isoString);
  if (label === "今日") return "success";
  if (label === "明日") return "warning";
  return "default";
}

/**
 * Get the initial character of a name for avatar display.
 */
export function getNameInitial(name: string): string {
  return name.charAt(0);
}
