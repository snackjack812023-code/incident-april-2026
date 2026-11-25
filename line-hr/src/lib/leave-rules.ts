// Pure leave rules, shared by the API (authoritative) and the LIFF form (preview only).
import { daysInclusive, addDays, isValidIsoDate, weekdayOf } from "./dates";

export type LeavePeriod = "full" | "morning" | "afternoon";

export const LEAVE_PERIODS: LeavePeriod[] = ["full", "morning", "afternoon"];
export const MAX_LEAVE_SPAN_DAYS = 60;

export const PERIOD_LABELS: Record<LeavePeriod, string> = {
  full: "เต็มวัน",
  morning: "ครึ่งวันเช้า",
  afternoon: "ครึ่งวันบ่าย",
};

export type LeaveDaysResult = { ok: true; days: number } | { ok: false; error: string };

/**
 * Counts leave days between two dates (inclusive), skipping non-working weekdays.
 * Half-day leave is 0.5 and must be a single working day.
 */
export function countLeaveDays(input: {
  startDate: string;
  endDate: string;
  period: LeavePeriod;
  workDays: readonly number[];
}): LeaveDaysResult {
  const { startDate, endDate, period, workDays } = input;
  if (!isValidIsoDate(startDate) || !isValidIsoDate(endDate)) {
    return { ok: false, error: "วันที่ไม่ถูกต้อง" };
  }
  if (endDate < startDate) return { ok: false, error: "วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่มลา" };

  const span = daysInclusive(startDate, endDate);
  if (span > MAX_LEAVE_SPAN_DAYS) {
    return { ok: false, error: `ลาได้ครั้งละไม่เกิน ${MAX_LEAVE_SPAN_DAYS} วัน` };
  }

  if (period !== "full") {
    if (startDate !== endDate) return { ok: false, error: "ลาครึ่งวันต้องเลือกวันเดียว" };
    if (!workDays.includes(weekdayOf(startDate))) return { ok: false, error: "วันที่เลือกเป็นวันหยุด" };
    return { ok: true, days: 0.5 };
  }

  let days = 0;
  for (let i = 0; i < span; i++) {
    if (workDays.includes(weekdayOf(addDays(startDate, i)))) days++;
  }
  if (days === 0) return { ok: false, error: "ช่วงวันที่เลือกเป็นวันหยุดทั้งหมด" };
  return { ok: true, days };
}

type Range = { startDate: string; endDate: string; period: LeavePeriod };

/** True if two leave requests cover the same time. A morning and an afternoon half-day on the same date don't clash. */
export function leaveRangesOverlap(a: Range, b: Range): boolean {
  if (a.endDate < b.startDate || b.endDate < a.startDate) return false;
  const bothHalfDaysSameDate =
    a.startDate === a.endDate &&
    b.startDate === b.endDate &&
    a.period !== "full" &&
    b.period !== "full" &&
    a.period !== b.period;
  return !bothHalfDaysSameDate;
}

/** "2 วัน", "0.5 วัน (ครึ่งวันเช้า)" */
export function formatLeaveDays(days: number, period: LeavePeriod): string {
  const amount = Number.isInteger(days) ? String(days) : days.toFixed(1);
  return period === "full" ? `${amount} วัน` : `${amount} วัน (${PERIOD_LABELS[period]})`;
}
