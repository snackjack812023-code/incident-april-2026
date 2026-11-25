// Thai labels shared by server and client code (no imports with side effects).
import type { EmployeeRole, LeaveStatus } from "@/db/schema";

export const STATUS_LABELS: Record<LeaveStatus, string> = {
  pending: "รออนุมัติ",
  approved: "อนุมัติแล้ว",
  rejected: "ปฏิเสธ",
  cancelled: "ยกเลิก",
};

export const ROLE_LABELS: Record<EmployeeRole, string> = {
  employee: "พนักงาน",
  manager: "หัวหน้างาน",
  admin: "แอดมิน",
};

export type DailyStatus = "present" | "late" | "leave" | "absent";

export const DAILY_STATUS_LABELS: Record<DailyStatus, string> = {
  present: "มาทำงาน",
  late: "มาสาย",
  leave: "ลา",
  absent: "ยังไม่เช็คอิน",
};

export const WEEKDAY_LABELS = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"];
