"use server";

// Every action re-checks the session and scopes changes to the actor's business:
// hidden form fields (ids) are never trusted on their own.
import { refresh } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getDb } from "@/db";
import type { EmployeeRole } from "@/db/schema";
import { requireAdmin, requireStaff } from "@/lib/auth";
import { createDeferredLineMessenger } from "@/lib/line/deferred";
import {
  createEmployee,
  resetLineLink,
  setEmployeeActive,
  updateEmployee,
  type EmployeeInput,
} from "@/lib/services/employees";
import { AppError } from "@/lib/services/errors";
import { decideLeave } from "@/lib/services/leaves";
import { createBranch, createLeaveType, updateBranch, updateBusiness, updateLeaveType } from "@/lib/services/setup";
import { SESSION_COOKIE } from "@/lib/session";

export type ActionState = { ok: boolean; message: string } | null;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ROLES: EmployeeRole[] = ["employee", "manager", "admin"];

function text(fd: FormData, key: string): string {
  const value = fd.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function id(fd: FormData, key = "id"): string {
  const value = text(fd, key);
  if (!UUID.test(value)) throw new AppError("invalid", "ข้อมูลไม่ถูกต้อง");
  return value;
}

function optionalNumber(fd: FormData, key: string): number | null {
  const raw = text(fd, key);
  if (!raw) return null;
  const n = Number(raw);
  if (!Number.isFinite(n)) throw new AppError("invalid", "กรุณากรอกตัวเลขให้ถูกต้อง");
  return n;
}

function integer(fd: FormData, key: string, fallback: number): number {
  const n = optionalNumber(fd, key);
  return n == null ? fallback : Math.round(n);
}

/** Runs a mutation, refreshes the page on success and turns AppErrors into form messages. */
async function run(fn: () => Promise<string>): Promise<ActionState> {
  try {
    const message = await fn();
    refresh();
    return { ok: true, message };
  } catch (err) {
    if (err instanceof AppError) return { ok: false, message: err.message };
    throw err;
  }
}

export async function decideLeaveAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireStaff("/admin/leaves");
  return run(async () => {
    const decision = text(fd, "decision") === "approve" ? "approve" : "reject";
    const result = await decideLeave(
      { db: getDb(), line: createDeferredLineMessenger() },
      me,
      { leaveId: id(fd, "leaveId"), decision, note: text(fd, "note") || null },
    );
    if (result.ok) return decision === "approve" ? "อนุมัติแล้ว" : "ปฏิเสธแล้ว";
    const messages = {
      forbidden: "คุณไม่มีสิทธิ์อนุมัติคำขอลา",
      not_found: "ไม่พบคำขอลานี้",
      own_request: "ไม่สามารถอนุมัติคำขอลาของตัวเองได้",
      already_decided: "คำขอนี้ถูกดำเนินการไปแล้ว",
    };
    throw new AppError(result.code, messages[result.code]);
  });
}

function employeeInput(fd: FormData): EmployeeInput {
  const name = text(fd, "name");
  const role = text(fd, "role") as EmployeeRole;
  if (!name) throw new AppError("invalid", "กรุณากรอกชื่อพนักงาน");
  if (!ROLES.includes(role)) throw new AppError("invalid", "ตำแหน่งสิทธิ์ไม่ถูกต้อง");
  const branchId = text(fd, "branchId");
  return {
    name,
    position: text(fd, "position") || null,
    role,
    branchId: branchId && UUID.test(branchId) ? branchId : null,
  };
}

export async function createEmployeeAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireAdmin("/admin/employees");
  return run(async () => {
    const employee = await createEmployee(getDb(), me.businessId, employeeInput(fd));
    return `เพิ่ม ${employee.name} แล้ว — รหัสเชิญ ${employee.inviteCode}`;
  });
}

export async function updateEmployeeAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireAdmin("/admin/employees");
  return run(async () => {
    const employeeId = id(fd);
    const input = employeeInput(fd);
    if (employeeId === me.id && input.role !== "admin") throw new AppError("self", "ไม่สามารถลดสิทธิ์ของตัวเองได้");
    await updateEmployee(getDb(), me.businessId, employeeId, input);
    return "บันทึกแล้ว";
  });
}

export async function resetLineLinkAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireAdmin("/admin/employees");
  return run(async () => {
    const employeeId = id(fd);
    if (employeeId === me.id) throw new AppError("self", "ไม่สามารถรีเซ็ตบัญชีของตัวเองได้");
    const code = await resetLineLink(getDb(), me.businessId, employeeId);
    return `ยกเลิกการผูก LINE แล้ว — รหัสเชิญใหม่ ${code}`;
  });
}

export async function setEmployeeActiveAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireAdmin("/admin/employees");
  return run(async () => {
    const employeeId = id(fd);
    if (employeeId === me.id) throw new AppError("self", "ไม่สามารถปิดใช้งานบัญชีของตัวเองได้");
    const active = text(fd, "active") === "true";
    await setEmployeeActive(getDb(), me.businessId, employeeId, active);
    return active ? "เปิดใช้งานแล้ว" : "ปิดใช้งานแล้ว";
  });
}

export async function updateBusinessAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireAdmin("/admin/settings");
  return run(async () => {
    const workDays = fd.getAll("workDays").map(Number);
    await updateBusiness(getDb(), me.businessId, { name: text(fd, "name"), workDays });
    return "บันทึกข้อมูลธุรกิจแล้ว";
  });
}

export async function saveBranchAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireAdmin("/admin/settings");
  return run(async () => {
    const input = {
      name: text(fd, "name"),
      latitude: optionalNumber(fd, "latitude"),
      longitude: optionalNumber(fd, "longitude"),
      radiusMeters: integer(fd, "radiusMeters", 150),
      workStart: text(fd, "workStart"),
      workEnd: text(fd, "workEnd"),
      lateGraceMinutes: integer(fd, "lateGraceMinutes", 0),
    };
    if (text(fd, "id")) {
      await updateBranch(getDb(), me.businessId, id(fd), input);
      return "บันทึกสาขาแล้ว";
    }
    await createBranch(getDb(), me.businessId, input);
    return "เพิ่มสาขาแล้ว";
  });
}

export async function saveLeaveTypeAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const me = await requireAdmin("/admin/settings");
  return run(async () => {
    const input = {
      name: text(fd, "name"),
      quotaDays: optionalNumber(fd, "quotaDays"),
      paid: fd.get("paid") === "on",
      active: text(fd, "id") ? fd.get("active") === "on" : true,
    };
    if (text(fd, "id")) {
      await updateLeaveType(getDb(), me.businessId, id(fd), input);
      return "บันทึกแล้ว";
    }
    await createLeaveType(getDb(), me.businessId, input);
    return "เพิ่มประเภทการลาแล้ว";
  });
}

export async function logoutAction(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/");
}
