import { and, asc, eq, gte, isNull, lte } from "drizzle-orm";
import { attendance, branches, employees, leaveRequests, leaveTypes, type Attendance, type Branch } from "@/db/schema";
import type { DB } from "@/db/types";
import { checkGeofence, earlyLeaveMinutes, lateMinutes, type GeofenceResult } from "../attendance-rules";
import { formatTime, zonedParts } from "../dates";
import { DAILY_STATUS_LABELS, type DailyStatus } from "../labels";
import { AppError, pgErrorCode } from "./errors";
import type { CurrentEmployee } from "./employees";

export type Position = { latitude: number; longitude: number } | null;

export type AttendanceContext = {
  date: string;
  time: string;
  branch: Branch | null;
  record: Attendance | null;
};

export async function getAttendanceContext(
  db: DB,
  employee: CurrentEmployee,
  now: Date = new Date(),
): Promise<AttendanceContext> {
  const { date, time } = zonedParts(now, employee.business.timezone);
  const [branchRows, recordRows] = await Promise.all([
    employee.branchId
      ? db
          .select()
          .from(branches)
          .where(and(eq(branches.id, employee.branchId), eq(branches.businessId, employee.businessId)))
      : Promise.resolve([] as Branch[]),
    db
      .select()
      .from(attendance)
      .where(and(eq(attendance.employeeId, employee.id), eq(attendance.workDate, date))),
  ]);
  return { date, time, branch: branchRows[0] ?? null, record: recordRows[0] ?? null };
}

function geofenceError(result: Exclude<GeofenceResult, { ok: true }>): AppError {
  if (result.reason === "location_required") {
    return new AppError("location_required", "กรุณาเปิดการเข้าถึงตำแหน่ง (GPS) เพื่อเช็คชื่อ");
  }
  return new AppError(
    "outside",
    `คุณอยู่นอกพื้นที่สาขา (ห่าง ${result.distance.toLocaleString("en-US")} ม. อนุญาตไม่เกิน ${result.radius} ม.)`,
  );
}

export async function checkIn(
  db: DB,
  employee: CurrentEmployee,
  position: Position,
  now: Date = new Date(),
): Promise<Attendance> {
  const tz = employee.business.timezone;
  const ctx = await getAttendanceContext(db, employee, now);
  if (!ctx.branch) throw new AppError("no_branch", "ยังไม่ได้กำหนดสาขาให้คุณ กรุณาติดต่อแอดมิน");
  if (ctx.record) {
    throw new AppError("already_checked_in", `วันนี้คุณเช็คอินแล้วเมื่อ ${formatTime(ctx.record.checkInAt, tz)} น.`);
  }

  const fence = checkGeofence(ctx.branch, position);
  if (!fence.ok) throw geofenceError(fence);

  const { minutes } = zonedParts(now, tz);
  try {
    const [row] = await db
      .insert(attendance)
      .values({
        businessId: employee.businessId,
        employeeId: employee.id,
        branchId: ctx.branch.id,
        workDate: ctx.date,
        checkInAt: now,
        checkInLat: position?.latitude ?? null,
        checkInLng: position?.longitude ?? null,
        checkInDistanceM: fence.distance,
        lateMinutes: lateMinutes(minutes, ctx.branch.workStart, ctx.branch.lateGraceMinutes),
      })
      .returning();
    return row;
  } catch (err) {
    if (pgErrorCode(err) === "23505") throw new AppError("already_checked_in", "วันนี้คุณเช็คอินแล้ว");
    throw err;
  }
}

export async function checkOut(
  db: DB,
  employee: CurrentEmployee,
  position: Position,
  now: Date = new Date(),
): Promise<Attendance> {
  const tz = employee.business.timezone;
  const ctx = await getAttendanceContext(db, employee, now);
  if (!ctx.record) throw new AppError("not_checked_in", "วันนี้คุณยังไม่ได้เช็คอิน");
  if (ctx.record.checkOutAt) {
    throw new AppError("already_checked_out", `วันนี้คุณเช็คเอาท์แล้วเมื่อ ${formatTime(ctx.record.checkOutAt, tz)} น.`);
  }

  let distance: number | null = null;
  let early = 0;
  if (ctx.branch) {
    const fence = checkGeofence(ctx.branch, position);
    if (!fence.ok) throw geofenceError(fence);
    distance = fence.distance;
    early = earlyLeaveMinutes(zonedParts(now, tz).minutes, ctx.branch.workEnd);
  }

  const [row] = await db
    .update(attendance)
    .set({
      checkOutAt: now,
      checkOutLat: position?.latitude ?? null,
      checkOutLng: position?.longitude ?? null,
      checkOutDistanceM: distance,
      earlyLeaveMinutes: early,
    })
    .where(and(eq(attendance.id, ctx.record.id), isNull(attendance.checkOutAt)))
    .returning();
  if (!row) throw new AppError("already_checked_out", "วันนี้คุณเช็คเอาท์แล้ว");
  return row;
}

export { DAILY_STATUS_LABELS, type DailyStatus };

/** One row per active employee for `date`: their check-in/out and approved leave, if any. */
export async function getDailyAttendance(db: DB, businessId: string, date: string) {
  const [people, records, leaves] = await Promise.all([
    db
      .select({ id: employees.id, name: employees.name, position: employees.position, branchId: employees.branchId })
      .from(employees)
      .where(and(eq(employees.businessId, businessId), eq(employees.active, true)))
      .orderBy(asc(employees.name)),
    db
      .select()
      .from(attendance)
      .where(and(eq(attendance.businessId, businessId), eq(attendance.workDate, date))),
    db
      .select({
        employeeId: leaveRequests.employeeId,
        period: leaveRequests.period,
        leaveTypeName: leaveTypes.name,
      })
      .from(leaveRequests)
      .innerJoin(leaveTypes, eq(leaveTypes.id, leaveRequests.leaveTypeId))
      .where(
        and(
          eq(leaveRequests.businessId, businessId),
          eq(leaveRequests.status, "approved"),
          lte(leaveRequests.startDate, date),
          gte(leaveRequests.endDate, date),
        ),
      ),
  ]);

  return people.map((person) => {
    const record = records.find((r) => r.employeeId === person.id) ?? null;
    const leave = leaves.find((l) => l.employeeId === person.id) ?? null;
    let status: DailyStatus;
    if (record) status = record.lateMinutes > 0 ? "late" : "present";
    else if (leave) status = "leave";
    else status = "absent";
    return { ...person, record, leave, status };
  });
}
