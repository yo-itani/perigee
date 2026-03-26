/**
 * Utility functions for the preparation feature.
 * Separated from components to avoid react-refresh warnings.
 *
 * Date formatting utilities are re-exported from the shared utils/date module.
 */

export {
  getRelativeLabel,
  formatScheduleDateTime,
  formatDateShort,
  formatCommentDate,
} from "@/utils/date";

/**
 * Get the added_by_tag display label.
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
