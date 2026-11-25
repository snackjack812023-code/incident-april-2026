import { and, eq } from "drizzle-orm";
import { branches, businesses, leaveTypes, type Branch, type Business } from "@/db/schema";
import type { DB } from "@/db/types";
import { parseHhmm } from "../dates";
import { AppError } from "./errors";
import { createEmployee } from "./employees";

/**
 * Starting leave types, based on the Thai Labour Protection Act minimums
 * (sick leave paid up to 30 days, personal business leave ≥ 3 days, annual leave ≥ 6 days
 * after one year of service). Adjust them per business in the settings page.
 */
export const DEFAULT_LEAVE_TYPES = [
  { name: "ลาป่วย", quotaDays: 30, paid: true },
  { name: "ลากิจ", quotaDays: 3, paid: true },
  { name: "ลาพักร้อน", quotaDays: 6, paid: true },
  { name: "ลาไม่รับค่าจ้าง", quotaDays: null, paid: false },
];

/** Creates a business with one branch, the default leave types and its first admin (with an invite code). */
export async function createBusinessWithDefaults(
  db: DB,
  input: { businessName: string; branchName?: string; adminName: string; workDays?: number[] },
) {
  return db.transaction(async (tx) => {
    const [business] = await tx
      .insert(businesses)
      .values({ name: input.businessName, ...(input.workDays ? { workDays: input.workDays } : {}) })
      .returning();
    const [branch] = await tx
      .insert(branches)
      .values({ businessId: business.id, name: input.branchName ?? "สาขาหลัก" })
      .returning();
    await tx
      .insert(leaveTypes)
      .values(DEFAULT_LEAVE_TYPES.map((type, i) => ({ ...type, businessId: business.id, sortOrder: i })));
    const admin = await createEmployee(tx, business.id, { name: input.adminName, role: "admin", branchId: branch.id });
    return { business, branch, admin };
  });
}

export async function getBusiness(db: DB, businessId: string): Promise<Business | null> {
  const [row] = await db.select().from(businesses).where(eq(businesses.id, businessId));
  return row ?? null;
}

export async function updateBusiness(db: DB, businessId: string, input: { name: string; workDays: number[] }) {
  const workDays = [...new Set(input.workDays)].filter((d) => d >= 0 && d <= 6).sort();
  if (!input.name.trim()) throw new AppError("invalid", "กรุณากรอกชื่อธุรกิจ");
  if (!workDays.length) throw new AppError("invalid", "ต้องมีวันทำงานอย่างน้อย 1 วัน");
  await db.update(businesses).set({ name: input.name.trim(), workDays }).where(eq(businesses.id, businessId));
}

export type BranchInput = Pick<
  Branch,
  "name" | "latitude" | "longitude" | "radiusMeters" | "workStart" | "workEnd" | "lateGraceMinutes"
>;

function validateBranch(input: BranchInput) {
  if (!input.name.trim()) throw new AppError("invalid", "กรุณากรอกชื่อสาขา");
  if ((input.latitude == null) !== (input.longitude == null)) {
    throw new AppError("invalid", "กรุณากรอกทั้งละติจูดและลองจิจูด หรือเว้นว่างทั้งคู่");
  }
  if (input.latitude != null && (Math.abs(input.latitude) > 90 || Math.abs(input.longitude ?? 0) > 180)) {
    throw new AppError("invalid", "พิกัดไม่ถูกต้อง");
  }
  if (Number.isNaN(parseHhmm(input.workStart)) || Number.isNaN(parseHhmm(input.workEnd))) {
    throw new AppError("invalid", "เวลาเข้า-ออกงานต้องเป็นรูปแบบ HH:MM");
  }
  if (input.radiusMeters < 20 || input.radiusMeters > 5000) throw new AppError("invalid", "รัศมีต้องอยู่ระหว่าง 20–5000 เมตร");
  if (input.lateGraceMinutes < 0 || input.lateGraceMinutes > 240) throw new AppError("invalid", "เวลาผ่อนผันไม่ถูกต้อง");
}

export async function createBranch(db: DB, businessId: string, input: BranchInput) {
  validateBranch(input);
  const [row] = await db
    .insert(branches)
    .values({ ...input, name: input.name.trim(), businessId })
    .returning();
  return row;
}

export async function updateBranch(db: DB, businessId: string, branchId: string, input: BranchInput) {
  validateBranch(input);
  await db
    .update(branches)
    .set({ ...input, name: input.name.trim() })
    .where(and(eq(branches.id, branchId), eq(branches.businessId, businessId)));
}

export type LeaveTypeInput = { name: string; quotaDays: number | null; paid: boolean; active: boolean };

function validateLeaveType(input: LeaveTypeInput) {
  if (!input.name.trim()) throw new AppError("invalid", "กรุณากรอกชื่อประเภทการลา");
  if (input.quotaDays != null && (input.quotaDays < 0 || input.quotaDays > 366 || (input.quotaDays * 2) % 1 !== 0)) {
    throw new AppError("invalid", "โควตาวันลาต้องเป็น 0–366 และลงท้ายด้วย .0 หรือ .5");
  }
}

export async function createLeaveType(db: DB, businessId: string, input: LeaveTypeInput) {
  validateLeaveType(input);
  await db.insert(leaveTypes).values({ ...input, name: input.name.trim(), businessId, sortOrder: 100 });
}

export async function updateLeaveType(db: DB, businessId: string, leaveTypeId: string, input: LeaveTypeInput) {
  validateLeaveType(input);
  await db
    .update(leaveTypes)
    .set({ ...input, name: input.name.trim() })
    .where(and(eq(leaveTypes.id, leaveTypeId), eq(leaveTypes.businessId, businessId)));
}
