import { and, asc, desc, eq, isNull } from "drizzle-orm";
import { branches, businesses, employees, type Employee, type EmployeeRole } from "@/db/schema";
import type { DB } from "@/db/types";
import { generateInviteCode, normalizeInviteCode } from "../invite-code";
import { ROLE_LABELS } from "../labels";
import { pgErrorCode } from "./errors";

export type BusinessInfo = { id: string; name: string; timezone: string; workDays: number[] };
export type CurrentEmployee = Employee & { business: BusinessInfo };

export { ROLE_LABELS };

export function isStaff(employee: Pick<Employee, "role">): boolean {
  return employee.role === "manager" || employee.role === "admin";
}

export async function findEmployeeByLineUserId(db: DB, lineUserId: string): Promise<CurrentEmployee | null> {
  const [row] = await db
    .select({
      employee: employees,
      business: {
        id: businesses.id,
        name: businesses.name,
        timezone: businesses.timezone,
        workDays: businesses.workDays,
      },
    })
    .from(employees)
    .innerJoin(businesses, eq(businesses.id, employees.businessId))
    .where(eq(employees.lineUserId, lineUserId))
    .limit(1);
  return row ? { ...row.employee, business: row.business } : null;
}

export async function updateLineProfile(
  db: DB,
  employeeId: string,
  profile: { displayName: string | null; pictureUrl: string | null },
): Promise<void> {
  await db
    .update(employees)
    .set({ lineDisplayName: profile.displayName, linePictureUrl: profile.pictureUrl })
    .where(eq(employees.id, employeeId));
}

export type LinkResult =
  | { ok: true; employee: CurrentEmployee }
  | { ok: false; code: "already_linked" | "invalid_code" };

/** Links a LINE account to the employee that owns `inviteCode`. Codes are single-use. */
export async function linkLineAccount(
  db: DB,
  input: { inviteCode: string; lineUserId: string; displayName?: string | null; pictureUrl?: string | null },
): Promise<LinkResult> {
  if (await findEmployeeByLineUserId(db, input.lineUserId)) return { ok: false, code: "already_linked" };

  const code = normalizeInviteCode(input.inviteCode);
  if (code.length < 6) return { ok: false, code: "invalid_code" };

  try {
    const updated = await db
      .update(employees)
      .set({
        lineUserId: input.lineUserId,
        lineDisplayName: input.displayName ?? null,
        linePictureUrl: input.pictureUrl ?? null,
        inviteCode: null,
      })
      .where(and(eq(employees.inviteCode, code), isNull(employees.lineUserId), eq(employees.active, true)))
      .returning({ id: employees.id });
    if (!updated.length) return { ok: false, code: "invalid_code" };
  } catch (err) {
    if (pgErrorCode(err) === "23505") return { ok: false, code: "already_linked" };
    throw err;
  }

  const employee = await findEmployeeByLineUserId(db, input.lineUserId);
  if (!employee) throw new Error("Linked employee not found");
  return { ok: true, employee };
}

async function insertWithUniqueInviteCode<T>(attempt: (code: string) => Promise<T>): Promise<T> {
  for (let i = 0; ; i++) {
    try {
      return await attempt(generateInviteCode());
    } catch (err) {
      // Retry the (astronomically rare) invite-code collision; rethrow anything else.
      if (pgErrorCode(err) !== "23505" || i >= 4) throw err;
    }
  }
}

async function assertBranchInBusiness(db: DB, businessId: string, branchId: string | null) {
  if (!branchId) return;
  const [branch] = await db
    .select({ id: branches.id })
    .from(branches)
    .where(and(eq(branches.id, branchId), eq(branches.businessId, businessId)));
  if (!branch) throw new Error("Branch does not belong to this business");
}

export type EmployeeInput = {
  name: string;
  position?: string | null;
  role: EmployeeRole;
  branchId?: string | null;
};

export async function createEmployee(db: DB, businessId: string, input: EmployeeInput): Promise<Employee> {
  let branchId = input.branchId ?? null;
  if (branchId) {
    await assertBranchInBusiness(db, businessId, branchId);
  } else {
    // Single-branch shops: default to the first branch.
    const [first] = await db
      .select({ id: branches.id })
      .from(branches)
      .where(eq(branches.businessId, businessId))
      .orderBy(asc(branches.createdAt))
      .limit(1);
    branchId = first?.id ?? null;
  }

  return insertWithUniqueInviteCode(async (inviteCode) => {
    const [row] = await db
      .insert(employees)
      .values({
        businessId,
        branchId,
        name: input.name.trim(),
        position: input.position?.trim() || null,
        role: input.role,
        inviteCode,
      })
      .returning();
    return row;
  });
}

export async function updateEmployee(
  db: DB,
  businessId: string,
  employeeId: string,
  input: EmployeeInput,
): Promise<void> {
  await assertBranchInBusiness(db, businessId, input.branchId ?? null);
  await db
    .update(employees)
    .set({
      name: input.name.trim(),
      position: input.position?.trim() || null,
      role: input.role,
      branchId: input.branchId ?? null,
    })
    .where(and(eq(employees.id, employeeId), eq(employees.businessId, businessId)));
}

export async function setEmployeeActive(db: DB, businessId: string, employeeId: string, active: boolean) {
  await db
    .update(employees)
    .set({ active })
    .where(and(eq(employees.id, employeeId), eq(employees.businessId, businessId)));
}

/** Unlinks the LINE account (e.g. new phone / wrong person) and issues a fresh invite code. */
export async function resetLineLink(db: DB, businessId: string, employeeId: string): Promise<string | null> {
  return insertWithUniqueInviteCode(async (inviteCode) => {
    const [row] = await db
      .update(employees)
      .set({ lineUserId: null, lineDisplayName: null, linePictureUrl: null, inviteCode })
      .where(and(eq(employees.id, employeeId), eq(employees.businessId, businessId)))
      .returning({ inviteCode: employees.inviteCode });
    return row?.inviteCode ?? null;
  });
}

export async function listEmployees(db: DB, businessId: string) {
  return db
    .select({
      id: employees.id,
      name: employees.name,
      position: employees.position,
      role: employees.role,
      active: employees.active,
      branchId: employees.branchId,
      branchName: branches.name,
      lineUserId: employees.lineUserId,
      lineDisplayName: employees.lineDisplayName,
      linePictureUrl: employees.linePictureUrl,
      inviteCode: employees.inviteCode,
    })
    .from(employees)
    .leftJoin(branches, eq(branches.id, employees.branchId))
    .where(eq(employees.businessId, businessId))
    .orderBy(desc(employees.active), asc(employees.createdAt));
}

export async function listBranches(db: DB, businessId: string) {
  return db.select().from(branches).where(eq(branches.businessId, businessId)).orderBy(asc(branches.createdAt));
}
