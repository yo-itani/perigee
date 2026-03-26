/**
 * Utility functions for the recording feature.
 * Separated from components to avoid react-refresh warnings.
 */

export { getRelativeLabel, formatScheduleDateTime } from "@/utils/date";

/**
 * Get the added_by_tag display label for agenda items.
 */
export function getAddedByTagLabel(tag: string): string {
  switch (tag) {
    case "organizer":
      return "オーガナイザーが追加";
    case "counterpart":
      return "カウンターパートが追加";
    case "template":
      return "テンプレート";
    default:
      return tag;
  }
}
