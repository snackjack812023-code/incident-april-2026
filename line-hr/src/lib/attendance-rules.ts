// Pure check-in rules: geofence distance and late / early-leave minutes.
import { parseHhmm } from "./dates";

const EARTH_RADIUS_M = 6_371_000;

/** Great-circle distance in metres (haversine). */
export function distanceMeters(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

export type GeofenceResult =
  | { ok: true; distance: number | null }
  | { ok: false; reason: "location_required" }
  | { ok: false; reason: "outside"; distance: number; radius: number };

/** A branch without coordinates has no geofence. */
export function checkGeofence(
  branch: { latitude: number | null; longitude: number | null; radiusMeters: number },
  position: { latitude: number; longitude: number } | null,
): GeofenceResult {
  if (branch.latitude == null || branch.longitude == null) return { ok: true, distance: null };
  if (!position) return { ok: false, reason: "location_required" };
  const distance = Math.round(distanceMeters(branch.latitude, branch.longitude, position.latitude, position.longitude));
  if (distance > branch.radiusMeters) return { ok: false, reason: "outside", distance, radius: branch.radiusMeters };
  return { ok: true, distance };
}

/** Minutes late, counted from the shift start once the grace period has passed (0 = on time). */
export function lateMinutes(nowMinutes: number, workStart: string, graceMinutes: number): number {
  const start = parseHhmm(workStart);
  if (Number.isNaN(start)) return 0;
  return nowMinutes > start + graceMinutes ? nowMinutes - start : 0;
}

/** Minutes left before the shift end (0 = left on time or later). */
export function earlyLeaveMinutes(nowMinutes: number, workEnd: string): number {
  const end = parseHhmm(workEnd);
  if (Number.isNaN(end)) return 0;
  return Math.max(0, end - nowMinutes);
}
