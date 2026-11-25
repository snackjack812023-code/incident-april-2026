import type { messagingApi, webhook } from "@line/bot-sdk";
import { eq } from "drizzle-orm";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { branches, leaveRequests } from "@/db/schema";
import type { DB } from "@/db/types";
import { FLEX_COLORS } from "@/lib/line/flex";
import { encodeLeaveDecision } from "@/lib/line/postback";
import { handleWebhookEvents } from "@/lib/line/webhook-handler";
import { checkIn, checkOut, getDailyAttendance } from "@/lib/services/attendance";
import { getDashboard } from "@/lib/services/dashboard";
import {
  createEmployee,
  findEmployeeByLineUserId,
  linkLineAccount,
  resetLineLink,
  type CurrentEmployee,
} from "@/lib/services/employees";
import { AppError } from "@/lib/services/errors";
import { cancelLeave, decideLeave, getLeaveBalances, getLeaveTypes, submitLeave } from "@/lib/services/leaves";
import { createBusinessWithDefaults } from "@/lib/services/setup";
import { createFakeMessenger, createTestDb } from "./helpers/db";

let db: DB;
let close: () => Promise<void>;
let line: ReturnType<typeof createFakeMessenger>;
let ctx: Awaited<ReturnType<typeof setup>>;

async function linkNew(businessId: string, name: string, role: "employee" | "manager" | "admin", lineUserId: string) {
  const employee = await createEmployee(db, businessId, { name, role });
  const result = await linkLineAccount(db, { inviteCode: employee.inviteCode!, lineUserId });
  if (!result.ok) throw new Error(result.code);
  return result.employee;
}

async function setup() {
  const { business, branch, admin } = await createBusinessWithDefaults(db, {
    businessName: "ร้านทดสอบ",
    adminName: "แอดมิน ทดสอบ",
  });
  const adminLink = await linkLineAccount(db, { inviteCode: admin.inviteCode!, lineUserId: "U_admin" });
  if (!adminLink.ok) throw new Error("admin link failed");
  const manager = await linkNew(business.id, "หัวหน้า สมชาย", "manager", "U_manager");
  const staff = await linkNew(business.id, "สมหญิง ใจดี", "employee", "U_staff");
  const types = await getLeaveTypes(db, business.id);
  const type = (name: string) => types.find((t) => t.name === name)!;
  return { business, branch, admin: adminLink.employee, manager, staff, type };
}

const reload = async (e: CurrentEmployee) => (await findEmployeeByLineUserId(db, e.lineUserId!))!;

beforeEach(async () => {
  ({ db, close } = await createTestDb());
  line = createFakeMessenger();
  ctx = await setup();
});

afterEach(async () => {
  await close();
});

describe("linking LINE accounts", () => {
  it("uses each invite code once and normalizes what people type", async () => {
    const employee = await createEmployee(db, ctx.business.id, { name: "พนักงานใหม่", role: "employee" });
    const typed = `${employee.inviteCode!.slice(0, 4).toLowerCase()}-${employee.inviteCode!.slice(4)}`;

    const first = await linkLineAccount(db, { inviteCode: typed, lineUserId: "U_new" });
    expect(first.ok).toBe(true);
    expect(first.ok && first.employee.inviteCode).toBeNull();

    expect(await linkLineAccount(db, { inviteCode: employee.inviteCode!, lineUserId: "U_other" })).toEqual({
      ok: false,
      code: "invalid_code",
    });
  });

  it("refuses a LINE account that is already linked", async () => {
    const employee = await createEmployee(db, ctx.business.id, { name: "อีกคน", role: "employee" });
    expect(await linkLineAccount(db, { inviteCode: employee.inviteCode!, lineUserId: "U_staff" })).toEqual({
      ok: false,
      code: "already_linked",
    });
  });

  it("can reset a link and issue a fresh code", async () => {
    const code = await resetLineLink(db, ctx.business.id, ctx.staff.id);
    expect(code).toMatch(/^[0-9A-Z]{8}$/);
    expect(await findEmployeeByLineUserId(db, "U_staff")).toBeNull();
  });
});

describe("leave requests", () => {
  it("creates a pending request and notifies every approver except the requester", async () => {
    const leave = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: ctx.type("ลาพักร้อน").id,
      startDate: "2026-11-20", // Friday
      endDate: "2026-11-23", // Monday → 2 working days
      period: "full",
      reason: "  ไปต่างจังหวัด  ",
    });
    expect(leave).toMatchObject({ status: "pending", days: 2, reason: "ไปต่างจังหวัด" });

    expect(line.sent).toHaveLength(1);
    expect(line.sent[0].op).toBe("multicast");
    expect([...(line.sent[0].to as string[])].sort()).toEqual(["U_admin", "U_manager"]);
    const card = line.sent[0].messages[0] as messagingApi.FlexMessage;
    expect((card.contents as messagingApi.FlexBubble).header?.backgroundColor).toBe(FLEX_COLORS.pending);
  });

  it("rejects overlapping requests but allows morning + afternoon on the same day", async () => {
    const base = { leaveTypeId: ctx.type("ลาป่วย").id, startDate: "2026-11-20", endDate: "2026-11-20" };
    await submitLeave({ db, line }, ctx.staff, { ...base, period: "morning" });
    await submitLeave({ db, line }, ctx.staff, { ...base, period: "afternoon" });
    await expect(submitLeave({ db, line }, ctx.staff, { ...base, period: "full" })).rejects.toMatchObject({
      code: "overlap",
    });
  });

  it("enforces the yearly quota, counting pending requests", async () => {
    const personal = ctx.type("ลากิจ").id; // 3 days
    await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: personal,
      startDate: "2026-11-16",
      endDate: "2026-11-18",
      period: "full",
    });
    const error = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: personal,
      startDate: "2026-11-25",
      endDate: "2026-11-25",
      period: "morning",
    }).catch((e) => e);
    expect(error).toBeInstanceOf(AppError);
    expect(error).toMatchObject({ code: "quota_exceeded" });

    const balances = await getLeaveBalances(db, ctx.staff, 2026);
    expect(balances.find((b) => b.leaveTypeId === personal)).toMatchObject({
      quotaDays: 3,
      usedDays: 0,
      pendingDays: 3,
      remainingDays: 0,
    });
  });

  it("lets a manager approve once and pushes a green card to the employee", async () => {
    const leave = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: ctx.type("ลาพักร้อน").id,
      startDate: "2026-12-01",
      endDate: "2026-12-02",
      period: "full",
    });
    line.sent.length = 0;

    const result = await decideLeave({ db, line }, ctx.manager, { leaveId: leave.id, decision: "approve" });
    expect(result).toMatchObject({ ok: true, leave: { status: "approved", deciderName: "หัวหน้า สมชาย" } });
    expect(line.sent).toEqual([expect.objectContaining({ op: "push", to: "U_staff" })]);
    const card = line.sent[0].messages[0] as messagingApi.FlexMessage;
    expect((card.contents as messagingApi.FlexBubble).header?.backgroundColor).toBe(FLEX_COLORS.approved);

    const again = await decideLeave({ db, line }, ctx.admin, { leaveId: leave.id, decision: "reject" });
    expect(again).toMatchObject({ ok: false, code: "already_decided", leave: { status: "approved" } });
    expect(line.sent).toHaveLength(1);
  });

  it("enforces who may decide", async () => {
    const staffLeave = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: ctx.type("ลาป่วย").id,
      startDate: "2026-12-07",
      endDate: "2026-12-07",
      period: "full",
    });
    expect(await decideLeave({ db, line }, ctx.staff, { leaveId: staffLeave.id, decision: "approve" })).toEqual({
      ok: false,
      code: "forbidden",
    });

    const managerLeave = await submitLeave({ db, line }, ctx.manager, {
      leaveTypeId: ctx.type("ลาป่วย").id,
      startDate: "2026-12-08",
      endDate: "2026-12-08",
      period: "full",
    });
    expect(await decideLeave({ db, line }, ctx.manager, { leaveId: managerLeave.id, decision: "approve" })).toMatchObject({
      ok: false,
      code: "own_request",
    });

    // Another business can't touch it at all.
    const other = await createBusinessWithDefaults(db, { businessName: "อีกร้าน", adminName: "เจ้าของอีกร้าน" });
    const otherAdmin = await linkLineAccount(db, { inviteCode: other.admin.inviteCode!, lineUserId: "U_other_admin" });
    if (!otherAdmin.ok) throw new Error("link failed");
    expect(
      await decideLeave({ db, line }, otherAdmin.employee, { leaveId: managerLeave.id, decision: "approve" }),
    ).toEqual({ ok: false, code: "not_found" });
  });

  it("lets employees cancel only while pending", async () => {
    const leave = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: ctx.type("ลาป่วย").id,
      startDate: "2026-12-09",
      endDate: "2026-12-09",
      period: "full",
    });
    expect(await cancelLeave(db, ctx.manager, leave.id)).toBe(false); // not theirs
    expect(await cancelLeave(db, ctx.staff, leave.id)).toBe(true);
    expect(await cancelLeave(db, ctx.staff, leave.id)).toBe(false); // already cancelled
  });
});

describe("attendance", () => {
  // 2026-11-20 is a Friday. Bangkok is UTC+7.
  const at = (hhmm: string) => new Date(`2026-11-20T${hhmm}:00+07:00`);
  const office = { latitude: 13.7462, longitude: 100.5347 };

  beforeEach(async () => {
    await db
      .update(branches)
      .set({ ...office, radiusMeters: 150, workStart: "09:00", workEnd: "18:00", lateGraceMinutes: 5 })
      .where(eq(branches.id, ctx.branch.id));
  });

  it("checks in inside the geofence, records lateness and refuses a second check-in", async () => {
    const staff = await reload(ctx.staff);
    await expect(checkIn(db, staff, { latitude: 13.7445, longitude: 100.53 }, at("08:50"))).rejects.toMatchObject({
      code: "outside",
    });
    await expect(checkIn(db, staff, null, at("08:50"))).rejects.toMatchObject({ code: "location_required" });

    const record = await checkIn(db, staff, office, at("09:12"));
    expect(record).toMatchObject({ workDate: "2026-11-20", lateMinutes: 12 });
    await expect(checkIn(db, staff, office, at("09:30"))).rejects.toMatchObject({ code: "already_checked_in" });

    const out = await checkOut(db, staff, office, at("17:30"));
    expect(out.earlyLeaveMinutes).toBe(30);
    await expect(checkOut(db, staff, office, at("18:30"))).rejects.toMatchObject({ code: "already_checked_out" });
  });

  it("summarises the day for the dashboard", async () => {
    await checkIn(db, await reload(ctx.manager), office, at("08:55"));
    await checkIn(db, await reload(ctx.admin), office, at("09:20"));
    const leave = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: ctx.type("ลาป่วย").id,
      startDate: "2026-11-20",
      endDate: "2026-11-20",
      period: "full",
    });
    await decideLeave({ db, line }, ctx.admin, { leaveId: leave.id, decision: "approve" });

    const daily = await getDailyAttendance(db, ctx.business.id, "2026-11-20");
    const statusOf = (name: string) => daily.find((d) => d.name === name)?.status;
    expect(statusOf("หัวหน้า สมชาย")).toBe("present");
    expect(statusOf("แอดมิน ทดสอบ")).toBe("late");
    expect(statusOf("สมหญิง ใจดี")).toBe("leave");

    expect(await getDashboard(db, ctx.business.id, "2026-11-20")).toMatchObject({
      totalEmployees: 3,
      checkedIn: 2,
      late: 1,
      onLeave: 1,
      pendingLeaves: 0,
    });
  });
});

describe("LINE webhook events", () => {
  const base = {
    timestamp: 0,
    mode: "active",
    webhookEventId: "01H",
    deliveryContext: { isRedelivery: false },
  };
  const event = (e: Record<string, unknown>) => ({ ...base, ...e }) as unknown as webhook.Event;

  it("approves a leave from a postback button and replies to the approver", async () => {
    const leave = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: ctx.type("ลาป่วย").id,
      startDate: "2026-12-14",
      endDate: "2026-12-14",
      period: "full",
    });
    line.sent.length = 0;

    await handleWebhookEvents({ db, line }, [
      event({
        type: "postback",
        replyToken: "reply-1",
        source: { type: "user", userId: "U_manager" },
        postback: { data: encodeLeaveDecision(leave.id, "approve") },
      }),
    ]);

    const [row] = await db.select().from(leaveRequests).where(eq(leaveRequests.id, leave.id));
    expect(row.status).toBe("approved");
    expect(line.sent.map((s) => [s.op, s.to])).toEqual([
      ["push", "U_staff"],
      ["reply", "reply-1"],
    ]);
    expect(line.sent[1].messages[0]).toMatchObject({ type: "text", text: expect.stringContaining("อนุมัติ") });
  });

  it("ignores postbacks from employees without permission", async () => {
    const leave = await submitLeave({ db, line }, ctx.staff, {
      leaveTypeId: ctx.type("ลาป่วย").id,
      startDate: "2026-12-15",
      endDate: "2026-12-15",
      period: "full",
    });
    line.sent.length = 0;
    await handleWebhookEvents({ db, line }, [
      event({
        type: "postback",
        replyToken: "reply-2",
        source: { type: "user", userId: "U_staff" },
        postback: { data: encodeLeaveDecision(leave.id, "approve") },
      }),
    ]);
    const [row] = await db.select().from(leaveRequests).where(eq(leaveRequests.id, leave.id));
    expect(row.status).toBe("pending");
    expect(line.sent).toEqual([
      expect.objectContaining({ op: "reply", messages: [{ type: "text", text: "คุณไม่มีสิทธิ์อนุมัติคำขอลา" }] }),
    ]);
  });

  it("greets new followers and answers menu keywords only in 1:1 chats", async () => {
    await handleWebhookEvents({ db, line }, [
      event({ type: "follow", replyToken: "r-follow", source: { type: "user", userId: "U_stranger" }, follow: {} }),
      event({
        type: "message",
        replyToken: "r-menu",
        source: { type: "user", userId: "U_staff" },
        message: { type: "text", id: "1", text: "เมนู", quoteToken: "q" },
      }),
      event({
        type: "message",
        replyToken: "r-chat",
        source: { type: "user", userId: "U_staff" },
        message: { type: "text", id: "2", text: "สวัสดีครับ", quoteToken: "q" },
      }),
      event({
        type: "message",
        replyToken: "r-group",
        source: { type: "group", groupId: "G1", userId: "U_staff" },
        message: { type: "text", id: "3", text: "เมนู", quoteToken: "q" },
      }),
    ]);
    expect(line.sent.map((s) => s.to)).toEqual(["r-follow", "r-menu"]);
    expect(JSON.stringify(line.sent[0].messages)).toContain("รหัสเชิญ");
    expect(JSON.stringify(line.sent[1].messages)).toContain("สมหญิง ใจดี");
  });
});
