import { z } from "zod";
import { getDb } from "@/db";
import { handleAppError, parseJson, unauthorized } from "@/lib/api";
import type { LeavesResponse } from "@/lib/api-types";
import { getCurrentEmployee } from "@/lib/auth";
import { zonedParts } from "@/lib/dates";
import { createDeferredLineMessenger } from "@/lib/line/deferred";
import { getLeaveBalances, listMyLeaves, submitLeave } from "@/lib/services/leaves";

export async function GET() {
  const me = await getCurrentEmployee();
  if (!me) return unauthorized();

  const db = getDb();
  const today = zonedParts(new Date(), me.business.timezone).date;
  const [balances, leaves] = await Promise.all([
    getLeaveBalances(db, me, Number(today.slice(0, 4))),
    listMyLeaves(db, me),
  ]);

  const body: LeavesResponse = {
    today,
    workDays: me.business.workDays,
    balances,
    leaves: leaves.map((l) => ({
      id: l.id,
      leaveTypeName: l.leaveTypeName,
      startDate: l.startDate,
      endDate: l.endDate,
      period: l.period,
      days: l.days,
      reason: l.reason,
      status: l.status,
      decisionNote: l.decisionNote,
      deciderName: l.deciderName,
    })),
  };
  return Response.json(body);
}

const Body = z.object({
  leaveTypeId: z.uuid({ error: "กรุณาเลือกประเภทการลา" }),
  startDate: z.iso.date({ error: "กรุณาเลือกวันที่เริ่มลา" }),
  endDate: z.iso.date({ error: "กรุณาเลือกวันที่สิ้นสุด" }),
  period: z.enum(["full", "morning", "afternoon"]),
  reason: z.string().trim().max(500, { error: "เหตุผลยาวเกินไป (ไม่เกิน 500 ตัวอักษร)" }).optional(),
});

export async function POST(req: Request) {
  const me = await getCurrentEmployee();
  if (!me) return unauthorized();

  const { data, error } = await parseJson(req, Body);
  if (error) return error;

  try {
    const leave = await submitLeave({ db: getDb(), line: createDeferredLineMessenger() }, me, data);
    return Response.json({ ok: true, id: leave.id, days: leave.days }, { status: 201 });
  } catch (err) {
    return handleAppError(err);
  }
}
