import { z } from "zod";
import { getDb } from "@/db";
import { handleAppError, parseJson, unauthorized } from "@/lib/api";
import type { AttendanceResponse } from "@/lib/api-types";
import { getCurrentEmployee } from "@/lib/auth";
import { formatTime } from "@/lib/dates";
import { checkIn, checkOut, getAttendanceContext } from "@/lib/services/attendance";
import type { CurrentEmployee } from "@/lib/services/employees";

async function snapshot(me: CurrentEmployee): Promise<AttendanceResponse> {
  const tz = me.business.timezone;
  const { date, time, branch, record } = await getAttendanceContext(getDb(), me);
  return {
    date,
    time,
    branch: branch && {
      name: branch.name,
      workStart: branch.workStart,
      workEnd: branch.workEnd,
      hasGeofence: branch.latitude != null && branch.longitude != null,
      radiusMeters: branch.radiusMeters,
    },
    record: record && {
      checkInTime: formatTime(record.checkInAt, tz),
      checkOutTime: record.checkOutAt ? formatTime(record.checkOutAt, tz) : null,
      lateMinutes: record.lateMinutes,
      earlyLeaveMinutes: record.earlyLeaveMinutes,
    },
  };
}

export async function GET() {
  const me = await getCurrentEmployee();
  if (!me) return unauthorized();
  return Response.json(await snapshot(me));
}

const Body = z.object({
  action: z.enum(["in", "out"]),
  latitude: z.number().min(-90).max(90).nullable().optional(),
  longitude: z.number().min(-180).max(180).nullable().optional(),
});

export async function POST(req: Request) {
  const me = await getCurrentEmployee();
  if (!me) return unauthorized();

  const { data, error } = await parseJson(req, Body);
  if (error) return error;

  const position =
    data.latitude != null && data.longitude != null ? { latitude: data.latitude, longitude: data.longitude } : null;
  try {
    if (data.action === "in") await checkIn(getDb(), me, position);
    else await checkOut(getDb(), me, position);
  } catch (err) {
    return handleAppError(err);
  }
  return Response.json(await snapshot(me));
}
