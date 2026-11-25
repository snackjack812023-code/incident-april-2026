import type { DB } from "@/db/types";
import { getDailyAttendance } from "./attendance";
import { countLeavesByStatus, listLeaves } from "./leaves";

export async function getDashboard(db: DB, businessId: string, today: string) {
  const [daily, counts, recentPending] = await Promise.all([
    getDailyAttendance(db, businessId, today),
    countLeavesByStatus(db, businessId),
    listLeaves(db, businessId, { status: "pending", limit: 5 }),
  ]);
  return {
    totalEmployees: daily.length,
    checkedIn: daily.filter((d) => d.record).length,
    late: daily.filter((d) => d.status === "late").length,
    onLeave: daily.filter((d) => d.leave).length,
    pendingLeaves: counts.pending,
    recentPending,
  };
}
