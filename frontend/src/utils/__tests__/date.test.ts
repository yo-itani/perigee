import { describe, expect, it, vi, afterEach } from "vitest";
import {
  getRelativeLabel,
  formatDateJa,
  formatTime,
  formatScheduleDateTime,
  formatDateShort,
  formatCommentDate,
} from "../date";

describe("getRelativeLabel", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "今日" for today', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 2, 26, 10, 0, 0)); // 2026-03-26 10:00
    expect(getRelativeLabel("2026-03-26T15:00:00")).toBe("今日");
  });

  it('returns "明日" for tomorrow', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 2, 26, 10, 0, 0));
    expect(getRelativeLabel("2026-03-27T09:00:00")).toBe("明日");
  });

  it('returns "昨日" for yesterday', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 2, 26, 10, 0, 0));
    expect(getRelativeLabel("2026-03-25T23:00:00")).toBe("昨日");
  });

  it('returns "N日後" for N days in the future', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 2, 26, 10, 0, 0));
    expect(getRelativeLabel("2026-03-29T10:00:00")).toBe("3日後");
  });

  it('returns "N日前" for N days in the past', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 2, 26, 10, 0, 0));
    expect(getRelativeLabel("2026-03-22T10:00:00")).toBe("4日前");
  });
});

describe("formatDateJa", () => {
  it("formats an ISO string to Japanese date with weekday", () => {
    // 2026-04-03 is a Friday
    expect(formatDateJa("2026-04-03T10:00:00")).toBe("2026年4月3日（金）");
  });

  it("formats a Sunday correctly", () => {
    // 2026-03-29 is a Sunday
    expect(formatDateJa("2026-03-29T10:00:00")).toBe("2026年3月29日（日）");
  });
});

describe("formatTime", () => {
  it("formats time as H:MM", () => {
    expect(formatTime("2026-04-03T10:05:00")).toBe("10:05");
  });

  it("pads minutes with leading zero", () => {
    expect(formatTime("2026-04-03T09:00:00")).toBe("9:00");
  });

  it("handles midnight", () => {
    expect(formatTime("2026-04-03T00:00:00")).toBe("0:00");
  });
});

describe("formatScheduleDateTime", () => {
  it("formats a full date-time string", () => {
    // 2026-04-03 is a Friday
    expect(formatScheduleDateTime("2026-04-03T10:00:00")).toBe(
      "2026/04/03（金）10:00",
    );
  });

  it("pads month and day with leading zeros", () => {
    // 2026-01-05 is a Monday
    expect(formatScheduleDateTime("2026-01-05T09:30:00")).toBe(
      "2026/01/05（月）9:30",
    );
  });
});

describe("formatDateShort", () => {
  it("formats an ISO string to YYYY/MM/DD", () => {
    expect(formatDateShort("2026-03-20T10:00:00")).toBe("2026/03/20");
  });

  it("pads single-digit month and day", () => {
    expect(formatDateShort("2026-01-05T00:00:00")).toBe("2026/01/05");
  });
});

describe("formatCommentDate", () => {
  it("formats as M月D日", () => {
    expect(formatCommentDate("2026-03-31T10:00:00")).toBe("3月31日");
  });

  it("handles single-digit month and day", () => {
    expect(formatCommentDate("2026-01-05T00:00:00")).toBe("1月5日");
  });
});
