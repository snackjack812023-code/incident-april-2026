import { describe, expect, it } from "vitest";
import { checkGeofence, distanceMeters, earlyLeaveMinutes, lateMinutes } from "@/lib/attendance-rules";
import { countLeaveDays, formatLeaveDays, leaveRangesOverlap } from "@/lib/leave-rules";

const MON_FRI = [1, 2, 3, 4, 5];

describe("countLeaveDays", () => {
  it("skips non-working days", () => {
    // Fri 20 Nov → Mon 23 Nov 2026 = Fri + Mon
    expect(countLeaveDays({ startDate: "2026-11-20", endDate: "2026-11-23", period: "full", workDays: MON_FRI })).toEqual({
      ok: true,
      days: 2,
    });
  });

  it("counts half days as 0.5 on a single working day", () => {
    expect(countLeaveDays({ startDate: "2026-11-20", endDate: "2026-11-20", period: "morning", workDays: MON_FRI })).toEqual({
      ok: true,
      days: 0.5,
    });
    expect(countLeaveDays({ startDate: "2026-11-20", endDate: "2026-11-21", period: "morning", workDays: MON_FRI }).ok).toBe(false);
    expect(countLeaveDays({ startDate: "2026-11-21", endDate: "2026-11-21", period: "afternoon", workDays: MON_FRI }).ok).toBe(false);
  });

  it("rejects bad ranges", () => {
    expect(countLeaveDays({ startDate: "2026-11-22", endDate: "2026-11-20", period: "full", workDays: MON_FRI }).ok).toBe(false);
    expect(countLeaveDays({ startDate: "2026-11-21", endDate: "2026-11-22", period: "full", workDays: MON_FRI })).toEqual({
      ok: false,
      error: "ช่วงวันที่เลือกเป็นวันหยุดทั้งหมด",
    });
    expect(countLeaveDays({ startDate: "2026-01-01", endDate: "2026-06-01", period: "full", workDays: MON_FRI }).ok).toBe(false);
  });
});

describe("leaveRangesOverlap", () => {
  const full = (startDate: string, endDate: string) => ({ startDate, endDate, period: "full" as const });

  it("detects overlapping and adjacent ranges", () => {
    expect(leaveRangesOverlap(full("2026-11-20", "2026-11-22"), full("2026-11-22", "2026-11-25"))).toBe(true);
    expect(leaveRangesOverlap(full("2026-11-20", "2026-11-22"), full("2026-11-23", "2026-11-25"))).toBe(false);
  });

  it("allows a morning and an afternoon half day on the same date", () => {
    const morning = { startDate: "2026-11-20", endDate: "2026-11-20", period: "morning" as const };
    const afternoon = { ...morning, period: "afternoon" as const };
    expect(leaveRangesOverlap(morning, afternoon)).toBe(false);
    expect(leaveRangesOverlap(morning, morning)).toBe(true);
    expect(leaveRangesOverlap(morning, full("2026-11-20", "2026-11-20"))).toBe(true);
  });

  it("formats day counts", () => {
    expect(formatLeaveDays(2, "full")).toBe("2 วัน");
    expect(formatLeaveDays(0.5, "morning")).toBe("0.5 วัน (ครึ่งวันเช้า)");
  });
});

describe("attendance rules", () => {
  it("measures distance with haversine", () => {
    // Δlat 0.0017° ≈ 189 m, Δlng 0.0047° at 13.7°N ≈ 508 m → ≈ 542 m.
    const d = distanceMeters(13.7462, 100.5347, 13.7445, 100.53);
    expect(d).toBeGreaterThan(450);
    expect(d).toBeLessThan(600);
  });

  it("applies the branch geofence", () => {
    const branch = { latitude: 13.7462, longitude: 100.5347, radiusMeters: 150 };
    expect(checkGeofence(branch, { latitude: 13.7463, longitude: 100.5348 }).ok).toBe(true);
    expect(checkGeofence(branch, { latitude: 13.7445, longitude: 100.53 })).toMatchObject({ ok: false, reason: "outside" });
    expect(checkGeofence(branch, null)).toEqual({ ok: false, reason: "location_required" });
    expect(checkGeofence({ latitude: null, longitude: null, radiusMeters: 150 }, null)).toEqual({ ok: true, distance: null });
  });

  it("computes late and early-leave minutes", () => {
    expect(lateMinutes(9 * 60 + 4, "09:00", 5)).toBe(0); // inside grace
    expect(lateMinutes(9 * 60 + 12, "09:00", 5)).toBe(12); // counted from shift start
    expect(earlyLeaveMinutes(17 * 60 + 30, "18:00")).toBe(30);
    expect(earlyLeaveMinutes(18 * 60 + 5, "18:00")).toBe(0);
  });
});
