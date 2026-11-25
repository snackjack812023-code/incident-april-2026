import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getDb } from "@/db";
import { findEmployeeByLineUserId, isStaff, type CurrentEmployee } from "./services/employees";
import { SESSION_COOKIE, verifySession } from "./session";

/** LINE user ID from the session cookie (set by /api/auth/line), or null. */
export async function getSessionLineUserId(): Promise<string | null> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  return token ? verifySession(token) : null;
}

/** The linked, active employee for this request. Role and status always come fresh from the DB. */
export async function getCurrentEmployee(): Promise<CurrentEmployee | null> {
  const lineUserId = await getSessionLineUserId();
  if (!lineUserId) return null;
  const employee = await findEmployeeByLineUserId(getDb(), lineUserId);
  return employee?.active ? employee : null;
}

/** For admin pages and server actions: managers and admins only. */
export async function requireStaff(nextPath = "/admin"): Promise<CurrentEmployee> {
  const me = await getCurrentEmployee();
  if (!me) redirect(`/liff/login?next=${encodeURIComponent(nextPath)}`);
  if (!isStaff(me)) redirect("/liff");
  return me;
}

/** Settings and employee management: admins only. */
export async function requireAdmin(nextPath = "/admin"): Promise<CurrentEmployee> {
  const me = await requireStaff(nextPath);
  if (me.role !== "admin") redirect("/admin");
  return me;
}
