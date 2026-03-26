/**
 * Utility functions for the dashboard feature.
 * Separated from components to avoid react-refresh warnings.
 *
 * Date formatting utilities are re-exported from the shared utils/date module.
 */

export { getRelativeLabel, formatDateJa, formatTime } from "@/utils/date";

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
