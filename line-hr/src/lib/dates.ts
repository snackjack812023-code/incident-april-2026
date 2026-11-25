// Pure date helpers. Dates are plain "YYYY-MM-DD" strings (no timezone); times are handled
// explicitly in the business timezone. Thai formatting is hard-coded so server and browser
// render exactly the same text (no ICU differences, no hydration mismatches).

export const THAI_MONTHS_SHORT = [
  "ม.ค.",
  "ก.พ.",
  "มี.ค.",
  "เม.ย.",
  "พ.ค.",
  "มิ.ย.",
  "ก.ค.",
  "ส.ค.",
  "ก.ย.",
  "ต.ค.",
  "พ.ย.",
  "ธ.ค.",
];

export const THAI_WEEKDAYS_SHORT = ["อา.", "จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส."];

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const DAY_MS = 86_400_000;

function toUtcMs(iso: string): number {
  const match = ISO_DATE.exec(iso);
  if (!match) throw new Error(`Invalid date: ${iso}`);
  const [, y, m, d] = match;
  return Date.UTC(Number(y), Number(m) - 1, Number(d));
}

function fromUtcMs(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

export function isValidIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  // Round-trip rejects things like 2026-02-30.
  return fromUtcMs(toUtcMs(value)) === value;
}

/** 0 = Sunday … 6 = Saturday */
export function weekdayOf(iso: string): number {
  return new Date(toUtcMs(iso)).getUTCDay();
}

export function addDays(iso: string, days: number): string {
  return fromUtcMs(toUtcMs(iso) + days * DAY_MS);
}

/** Number of calendar days from start to end, counting both ends. */
export function daysInclusive(start: string, end: string): number {
  return Math.round((toUtcMs(end) - toUtcMs(start)) / DAY_MS) + 1;
}

function parts(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return { y, m, d, be: y + 543 };
}

/** "20 พ.ย. 2569" (Buddhist era). */
export function formatThaiDate(iso: string, opts: { weekday?: boolean } = {}): string {
  const { m, d, be } = parts(iso);
  const text = `${d} ${THAI_MONTHS_SHORT[m - 1]} ${be}`;
  return opts.weekday ? `${THAI_WEEKDAYS_SHORT[weekdayOf(iso)]} ${text}` : text;
}

/** "20 พ.ย. 2569", "20–22 พ.ย. 2569", "30 พ.ย. – 2 ธ.ค. 2569", "30 ธ.ค. 2569 – 2 ม.ค. 2570" */
export function formatThaiDateRange(start: string, end: string): string {
  if (start === end) return formatThaiDate(start);
  const a = parts(start);
  const b = parts(end);
  if (a.y === b.y && a.m === b.m) return `${a.d}–${b.d} ${THAI_MONTHS_SHORT[b.m - 1]} ${b.be}`;
  if (a.y === b.y) return `${a.d} ${THAI_MONTHS_SHORT[a.m - 1]} – ${b.d} ${THAI_MONTHS_SHORT[b.m - 1]} ${b.be}`;
  return `${formatThaiDate(start)} – ${formatThaiDate(end)}`;
}

const formatterCache = new Map<string, Intl.DateTimeFormat>();

function zonedFormatter(timeZone: string): Intl.DateTimeFormat {
  let fmt = formatterCache.get(timeZone);
  if (!fmt) {
    fmt = new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    });
    formatterCache.set(timeZone, fmt);
  }
  return fmt;
}

/** Local calendar date and minutes-since-midnight of `instant` in `timeZone`. */
export function zonedParts(instant: Date, timeZone: string): { date: string; minutes: number; time: string } {
  const p: Record<string, string> = {};
  for (const part of zonedFormatter(timeZone).formatToParts(instant)) p[part.type] = part.value;
  const hour = Number(p.hour) % 24;
  const minute = Number(p.minute);
  return {
    date: `${p.year}-${p.month}-${p.day}`,
    minutes: hour * 60 + minute,
    time: `${String(hour).padStart(2, "0")}:${p.minute}`,
  };
}

/** "09:30" → 570. Returns NaN for malformed input. */
export function parseHhmm(value: string): number {
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(value);
  if (!match) return Number.NaN;
  return Number(match[1]) * 60 + Number(match[2]);
}

export function formatThaiDateTime(instant: Date, timeZone: string): string {
  const { date, time } = zonedParts(instant, timeZone);
  return `${formatThaiDate(date)} ${time} น.`;
}

export function formatTime(instant: Date, timeZone: string): string {
  return zonedParts(instant, timeZone).time;
}
