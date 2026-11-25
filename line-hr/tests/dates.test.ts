import { describe, expect, it } from "vitest";
import {
  addDays,
  daysInclusive,
  formatThaiDate,
  formatThaiDateRange,
  isValidIsoDate,
  parseHhmm,
  weekdayOf,
  zonedParts,
} from "@/lib/dates";

describe("dates", () => {
  it("validates ISO dates including impossible days", () => {
    expect(isValidIsoDate("2026-11-20")).toBe(true);
    expect(isValidIsoDate("2026-02-30")).toBe(false);
    expect(isValidIsoDate("2026-2-3")).toBe(false);
  });

  it("does calendar math without timezone drift", () => {
    expect(weekdayOf("2026-11-20")).toBe(5); // Friday
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(daysInclusive("2026-11-20", "2026-11-22")).toBe(3);
  });

  it("formats Thai dates in the Buddhist era", () => {
    expect(formatThaiDate("2026-11-20")).toBe("20 พ.ย. 2569");
    expect(formatThaiDate("2026-11-20", { weekday: true })).toBe("ศ. 20 พ.ย. 2569");
    expect(formatThaiDateRange("2026-11-20", "2026-11-22")).toBe("20–22 พ.ย. 2569");
    expect(formatThaiDateRange("2026-11-30", "2026-12-02")).toBe("30 พ.ย. – 2 ธ.ค. 2569");
    expect(formatThaiDateRange("2026-12-30", "2027-01-02")).toBe("30 ธ.ค. 2569 – 2 ม.ค. 2570");
  });

  it("reads local date and time in the business timezone", () => {
    // 2026-11-20 23:30 UTC is already 06:30 on the 21st in Bangkok (UTC+7).
    const local = zonedParts(new Date("2026-11-20T23:30:00Z"), "Asia/Bangkok");
    expect(local).toEqual({ date: "2026-11-21", minutes: 6 * 60 + 30, time: "06:30" });
  });

  it("parses HH:MM", () => {
    expect(parseHhmm("09:30")).toBe(570);
    expect(parseHhmm("24:00")).toBeNaN();
  });
});
