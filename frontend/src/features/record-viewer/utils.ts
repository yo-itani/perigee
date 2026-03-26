/**
 * Utility functions for the record-viewer feature.
 * Separated from components to avoid react-refresh warnings.
 */

export {
  formatScheduleDateTime,
  formatDateShort,
  formatCommentDate,
  formatDateJa,
  formatTime,
} from "@/utils/date";

import type { RecordViewerRole } from "./types";

/**
 * Determine the viewer's role relative to a record.
 */
export function determineRole(
  currentUserId: string,
  organizerId: string,
  counterpartId: string,
): RecordViewerRole {
  if (currentUserId === organizerId) return "organizer";
  if (currentUserId === counterpartId) return "counterpart";
  return "viewer";
}

/**
 * Format duration in minutes to a display string.
 */
export function formatDuration(minutes: number | undefined): string {
  if (minutes == null) return "-";
  return `${minutes}分`;
}

/**
 * Get abbreviated name (first character) for an avatar.
 */
export function getAvatarInitial(userId: string): string {
  return userId.slice(0, 1).toUpperCase();
}
