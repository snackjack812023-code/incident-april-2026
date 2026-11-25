// Response shapes shared by the API routes and the LIFF client pages (types only).
import type { EmployeeRole, LeaveStatus } from "@/db/schema";
import type { LeavePeriod } from "./leave-rules";

export type PublicEmployee = {
  id: string;
  name: string;
  role: EmployeeRole;
  position: string | null;
  businessName: string;
};

export type AuthResponse = {
  profile: { displayName: string | null; pictureUrl: string | null };
  employee: PublicEmployee | null;
};

export type LeaveBalanceDto = {
  leaveTypeId: string;
  name: string;
  paid: boolean;
  quotaDays: number | null;
  usedDays: number;
  pendingDays: number;
  remainingDays: number | null;
};

export type MyLeaveDto = {
  id: string;
  leaveTypeName: string;
  startDate: string;
  endDate: string;
  period: LeavePeriod;
  days: number;
  reason: string | null;
  status: LeaveStatus;
  decisionNote: string | null;
  deciderName: string | null;
};

export type LeavesResponse = {
  today: string;
  workDays: number[];
  balances: LeaveBalanceDto[];
  leaves: MyLeaveDto[];
};

export type AttendanceResponse = {
  date: string;
  time: string;
  branch: {
    name: string;
    workStart: string;
    workEnd: string;
    hasGeofence: boolean;
    radiusMeters: number;
  } | null;
  record: {
    checkInTime: string;
    checkOutTime: string | null;
    lateMinutes: number;
    earlyLeaveMinutes: number;
  } | null;
};

export type ApiErrorBody = { error: { code: string; message: string } };
