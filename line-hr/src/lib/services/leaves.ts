import { and, asc, count, desc, eq, gte, inArray, isNotNull, lte, ne, sql } from "drizzle-orm";
import { alias } from "drizzle-orm/pg-core";
import { employees, leaveRequests, leaveTypes, type LeaveRequest, type LeaveStatus } from "@/db/schema";
import type { DB } from "@/db/types";
import { countLeaveDays, leaveRangesOverlap, type LeavePeriod } from "../leave-rules";
import { leaveDecisionMessage, newLeaveRequestMessage } from "../line/flex";
import type { LineMessenger } from "../line/messenger";
import type { LeaveDecision } from "../line/postback";
import { adminUrl, liffUrl } from "../urls";
import { STATUS_LABELS } from "../labels";
import { AppError } from "./errors";
import type { CurrentEmployee } from "./employees";

export type LeaveDeps = { db: DB; line: LineMessenger };

const ACTIVE_STATUSES: LeaveStatus[] = ["pending", "approved"];

export { STATUS_LABELS };

export async function getLeaveTypes(db: DB, businessId: string, opts: { includeInactive?: boolean } = {}) {
  return db
    .select()
    .from(leaveTypes)
    .where(
      opts.includeInactive
        ? eq(leaveTypes.businessId, businessId)
        : and(eq(leaveTypes.businessId, businessId), eq(leaveTypes.active, true)),
    )
    .orderBy(asc(leaveTypes.sortOrder), asc(leaveTypes.createdAt));
}

function yearRange(year: number) {
  return { from: `${year}-01-01`, to: `${year}-12-31` };
}

export type LeaveBalance = {
  leaveTypeId: string;
  name: string;
  paid: boolean;
  quotaDays: number | null;
  usedDays: number;
  pendingDays: number;
  /** What can still be requested this year (quota − approved − pending). Null = unlimited. */
  remainingDays: number | null;
};

/** Per-type usage for the calendar year. A request counts toward the year its start date falls in. */
export async function getLeaveBalances(db: DB, employee: CurrentEmployee, year: number): Promise<LeaveBalance[]> {
  const { from, to } = yearRange(year);
  const [types, usage] = await Promise.all([
    getLeaveTypes(db, employee.businessId),
    db
      .select({
        leaveTypeId: leaveRequests.leaveTypeId,
        status: leaveRequests.status,
        days: sql<number>`sum(${leaveRequests.days})`.mapWith(Number),
      })
      .from(leaveRequests)
      .where(
        and(
          eq(leaveRequests.employeeId, employee.id),
          inArray(leaveRequests.status, ACTIVE_STATUSES),
          gte(leaveRequests.startDate, from),
          lte(leaveRequests.startDate, to),
        ),
      )
      .groupBy(leaveRequests.leaveTypeId, leaveRequests.status),
  ]);

  return types.map((type) => {
    const sum = (status: LeaveStatus) =>
      usage.find((u) => u.leaveTypeId === type.id && u.status === status)?.days ?? 0;
    const usedDays = sum("approved");
    const pendingDays = sum("pending");
    return {
      leaveTypeId: type.id,
      name: type.name,
      paid: type.paid,
      quotaDays: type.quotaDays,
      usedDays,
      pendingDays,
      remainingDays: type.quotaDays == null ? null : Math.max(0, type.quotaDays - usedDays - pendingDays),
    };
  });
}

export type LeaveInput = {
  leaveTypeId: string;
  startDate: string;
  endDate: string;
  period: LeavePeriod;
  reason?: string | null;
};

export async function submitLeave(deps: LeaveDeps, employee: CurrentEmployee, input: LeaveInput): Promise<LeaveRequest> {
  const { db, line } = deps;

  const [type] = await db
    .select()
    .from(leaveTypes)
    .where(
      and(
        eq(leaveTypes.id, input.leaveTypeId),
        eq(leaveTypes.businessId, employee.businessId),
        eq(leaveTypes.active, true),
      ),
    );
  if (!type) throw new AppError("invalid_type", "ไม่พบประเภทการลานี้");

  const counted = countLeaveDays({ ...input, workDays: employee.business.workDays });
  if (!counted.ok) throw new AppError("invalid_dates", counted.error);

  const created = await db.transaction(async (tx) => {
    // Lock the employee row so two quick submissions can't both pass the overlap / quota checks.
    await tx.select({ id: employees.id }).from(employees).where(eq(employees.id, employee.id)).for("update");

    const nearby = await tx
      .select({ startDate: leaveRequests.startDate, endDate: leaveRequests.endDate, period: leaveRequests.period })
      .from(leaveRequests)
      .where(
        and(
          eq(leaveRequests.employeeId, employee.id),
          inArray(leaveRequests.status, ACTIVE_STATUSES),
          lte(leaveRequests.startDate, input.endDate),
          gte(leaveRequests.endDate, input.startDate),
        ),
      );
    if (nearby.some((other) => leaveRangesOverlap(other, input))) {
      throw new AppError("overlap", "มีคำขอลาในช่วงวันที่นี้อยู่แล้ว");
    }

    if (type.quotaDays != null) {
      const { from, to } = yearRange(Number(input.startDate.slice(0, 4)));
      const [{ total }] = await tx
        .select({ total: sql<number>`coalesce(sum(${leaveRequests.days}), 0)`.mapWith(Number) })
        .from(leaveRequests)
        .where(
          and(
            eq(leaveRequests.employeeId, employee.id),
            eq(leaveRequests.leaveTypeId, type.id),
            inArray(leaveRequests.status, ACTIVE_STATUSES),
            gte(leaveRequests.startDate, from),
            lte(leaveRequests.startDate, to),
          ),
        );
      if (total + counted.days > type.quotaDays) {
        const left = Math.max(0, type.quotaDays - total);
        throw new AppError("quota_exceeded", `${type.name}คงเหลือไม่พอ (เหลือ ${left} วัน)`);
      }
    }

    const [row] = await tx
      .insert(leaveRequests)
      .values({
        businessId: employee.businessId,
        employeeId: employee.id,
        leaveTypeId: type.id,
        startDate: input.startDate,
        endDate: input.endDate,
        period: input.period,
        days: counted.days,
        reason: input.reason?.trim() || null,
      })
      .returning();
    return row;
  });

  const approvers = await db
    .select({ lineUserId: employees.lineUserId })
    .from(employees)
    .where(
      and(
        eq(employees.businessId, employee.businessId),
        eq(employees.active, true),
        inArray(employees.role, ["manager", "admin"]),
        isNotNull(employees.lineUserId),
        ne(employees.id, employee.id),
      ),
    );
  const recipients = approvers.flatMap((a) => (a.lineUserId ? [a.lineUserId] : []));
  if (recipients.length) {
    await line.multicast(recipients, [
      newLeaveRequestMessage(
        { ...created, employeeName: employee.name, leaveTypeName: type.name },
        { reviewUrl: adminUrl("/leaves") },
      ),
    ]);
  }
  return created;
}

const decider = alias(employees, "decider");

function leaveDetailQuery(db: DB) {
  return db
    .select({
      leave: leaveRequests,
      employeeName: employees.name,
      employeeLineUserId: employees.lineUserId,
      leaveTypeName: leaveTypes.name,
      paid: leaveTypes.paid,
      deciderName: decider.name,
    })
    .from(leaveRequests)
    .innerJoin(employees, eq(employees.id, leaveRequests.employeeId))
    .innerJoin(leaveTypes, eq(leaveTypes.id, leaveRequests.leaveTypeId))
    .leftJoin(decider, eq(decider.id, leaveRequests.decidedById));
}

export type LeaveDetail = LeaveRequest & {
  employeeName: string;
  employeeLineUserId: string | null;
  leaveTypeName: string;
  paid: boolean;
  deciderName: string | null;
};

function toDetail(row: { leave: LeaveRequest } & Omit<LeaveDetail, keyof LeaveRequest>): LeaveDetail {
  const { leave, ...rest } = row;
  return { ...leave, ...rest };
}

export async function getLeaveDetail(db: DB, businessId: string, leaveId: string): Promise<LeaveDetail | null> {
  const [row] = await leaveDetailQuery(db).where(
    and(eq(leaveRequests.id, leaveId), eq(leaveRequests.businessId, businessId)),
  );
  return row ? toDetail(row) : null;
}

export async function listLeaves(
  db: DB,
  businessId: string,
  opts: { status?: LeaveStatus; limit?: number } = {},
): Promise<LeaveDetail[]> {
  const where = opts.status
    ? and(eq(leaveRequests.businessId, businessId), eq(leaveRequests.status, opts.status))
    : eq(leaveRequests.businessId, businessId);
  const rows = await leaveDetailQuery(db)
    .where(where)
    // Pending: oldest first (first come, first served). Everything else: newest first.
    .orderBy(opts.status === "pending" ? asc(leaveRequests.createdAt) : desc(leaveRequests.createdAt))
    .limit(opts.limit ?? 100);
  return rows.map(toDetail);
}

export async function countLeavesByStatus(db: DB, businessId: string): Promise<Record<LeaveStatus, number>> {
  const rows = await db
    .select({ status: leaveRequests.status, n: count() })
    .from(leaveRequests)
    .where(eq(leaveRequests.businessId, businessId))
    .groupBy(leaveRequests.status);
  const result: Record<LeaveStatus, number> = { pending: 0, approved: 0, rejected: 0, cancelled: 0 };
  for (const row of rows) result[row.status] = row.n;
  return result;
}

export async function listMyLeaves(db: DB, employee: CurrentEmployee, limit = 20): Promise<LeaveDetail[]> {
  const rows = await leaveDetailQuery(db)
    .where(eq(leaveRequests.employeeId, employee.id))
    .orderBy(desc(leaveRequests.startDate), desc(leaveRequests.createdAt))
    .limit(limit);
  return rows.map(toDetail);
}

export type DecideResult =
  | { ok: true; leave: LeaveDetail }
  | { ok: false; code: "forbidden" | "not_found" | "own_request" | "already_decided"; leave?: LeaveDetail };

/**
 * Approves or rejects a pending request. Safe to call twice (double tap, LINE redelivery):
 * only the first call changes anything, later ones get "already_decided".
 */
export async function decideLeave(
  deps: LeaveDeps,
  actor: CurrentEmployee,
  input: { leaveId: string; decision: LeaveDecision; note?: string | null },
): Promise<DecideResult> {
  const { db, line } = deps;
  if (!actor.active || (actor.role !== "manager" && actor.role !== "admin")) return { ok: false, code: "forbidden" };

  const leave = await getLeaveDetail(db, actor.businessId, input.leaveId);
  if (!leave) return { ok: false, code: "not_found" };
  // Managers can't approve their own leave; the admin (owner) can.
  if (leave.employeeId === actor.id && actor.role !== "admin") return { ok: false, code: "own_request", leave };

  const status = input.decision === "approve" ? "approved" : "rejected";
  const updated = await db
    .update(leaveRequests)
    .set({ status, decidedById: actor.id, decidedAt: new Date(), decisionNote: input.note?.trim() || null })
    .where(
      and(
        eq(leaveRequests.id, leave.id),
        eq(leaveRequests.businessId, actor.businessId),
        eq(leaveRequests.status, "pending"),
      ),
    )
    .returning({ id: leaveRequests.id });

  const current = (await getLeaveDetail(db, actor.businessId, leave.id)) ?? leave;
  if (!updated.length) return { ok: false, code: "already_decided", leave: current };

  if (current.employeeLineUserId) {
    await line.push(current.employeeLineUserId, [
      leaveDecisionMessage(
        { ...current, status, deciderName: actor.name, note: current.decisionNote },
        { detailsUrl: liffUrl("/leave") },
      ),
    ]);
  }
  return { ok: true, leave: current };
}

/** Employees can withdraw their own request while it is still pending. */
export async function cancelLeave(db: DB, employee: CurrentEmployee, leaveId: string): Promise<boolean> {
  const rows = await db
    .update(leaveRequests)
    .set({ status: "cancelled" })
    .where(
      and(
        eq(leaveRequests.id, leaveId),
        eq(leaveRequests.employeeId, employee.id),
        eq(leaveRequests.status, "pending"),
      ),
    )
    .returning({ id: leaveRequests.id });
  return rows.length > 0;
}
