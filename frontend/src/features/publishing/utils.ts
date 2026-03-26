/**
 * Utility functions for the publishing feature.
 * Separated from components to avoid react-refresh warnings.
 */

export { formatScheduleDateTime } from "@/utils/date";

/**
 * Get a display label for the record status.
 */
export function getStatusLabel(status: string): string {
  switch (status) {
    case "draft":
      return "下書き";
    case "published":
      return "公開済み";
    default:
      return status;
  }
}
