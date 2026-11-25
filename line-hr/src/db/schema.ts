import { sql } from "drizzle-orm";
import {
  boolean,
  check,
  date,
  doublePrecision,
  index,
  integer,
  numeric,
  pgEnum,
  pgTable,
  smallint,
  text,
  timestamp,
  uniqueIndex,
  uuid,
  varchar,
} from "drizzle-orm/pg-core";

export const employeeRole = pgEnum("employee_role", ["employee", "manager", "admin"]);
export const leavePeriod = pgEnum("leave_period", ["full", "morning", "afternoon"]);
export const leaveStatus = pgEnum("leave_status", ["pending", "approved", "rejected", "cancelled"]);

const createdAt = () => timestamp("created_at", { withTimezone: true }).notNull().defaultNow();

/** One row per customer (shop / company). Every other table hangs off this for multi-tenancy. */
export const businesses = pgTable("businesses", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: text("name").notNull(),
  timezone: text("timezone").notNull().default("Asia/Bangkok"),
  /** Working weekdays, 0 = Sunday … 6 = Saturday. Leave days are only counted on these days. */
  workDays: smallint("work_days").array().notNull().default(sql`'{1,2,3,4,5}'::smallint[]`),
  createdAt: createdAt(),
});

export const branches = pgTable(
  "branches",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    businessId: uuid("business_id")
      .notNull()
      .references(() => businesses.id, { onDelete: "cascade" }),
    name: text("name").notNull(),
    /** Check-in geofence. When latitude/longitude are null, check-in is accepted from anywhere. */
    latitude: doublePrecision("latitude"),
    longitude: doublePrecision("longitude"),
    radiusMeters: integer("radius_meters").notNull().default(150),
    /** Shift times as "HH:MM" in the business timezone. */
    workStart: varchar("work_start", { length: 5 }).notNull().default("09:00"),
    workEnd: varchar("work_end", { length: 5 }).notNull().default("18:00"),
    lateGraceMinutes: integer("late_grace_minutes").notNull().default(0),
    createdAt: createdAt(),
  },
  (t) => [index("branches_business_idx").on(t.businessId)],
);

export const employees = pgTable(
  "employees",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    businessId: uuid("business_id")
      .notNull()
      .references(() => businesses.id, { onDelete: "cascade" }),
    branchId: uuid("branch_id").references(() => branches.id, { onDelete: "set null" }),
    name: text("name").notNull(),
    position: text("position"),
    role: employeeRole("role").notNull().default("employee"),
    active: boolean("active").notNull().default(true),
    /** LINE user ID (from LIFF / webhook). Same value only if LINE Login and Messaging API channels share a provider. */
    lineUserId: text("line_user_id").unique(),
    lineDisplayName: text("line_display_name"),
    linePictureUrl: text("line_picture_url"),
    /** One-time code the employee types in LIFF to link their LINE account. Cleared after linking. */
    inviteCode: varchar("invite_code", { length: 12 }).unique(),
    createdAt: createdAt(),
  },
  (t) => [index("employees_business_idx").on(t.businessId)],
);

export const leaveTypes = pgTable(
  "leave_types",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    businessId: uuid("business_id")
      .notNull()
      .references(() => businesses.id, { onDelete: "cascade" }),
    name: text("name").notNull(),
    /** Days per calendar year. Null = no limit. */
    quotaDays: numeric("quota_days", { precision: 5, scale: 1, mode: "number" }),
    paid: boolean("paid").notNull().default(true),
    active: boolean("active").notNull().default(true),
    sortOrder: integer("sort_order").notNull().default(0),
    createdAt: createdAt(),
  },
  (t) => [index("leave_types_business_idx").on(t.businessId)],
);

export const leaveRequests = pgTable(
  "leave_requests",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    businessId: uuid("business_id")
      .notNull()
      .references(() => businesses.id, { onDelete: "cascade" }),
    employeeId: uuid("employee_id")
      .notNull()
      .references(() => employees.id, { onDelete: "cascade" }),
    leaveTypeId: uuid("leave_type_id")
      .notNull()
      .references(() => leaveTypes.id, { onDelete: "restrict" }),
    startDate: date("start_date", { mode: "string" }).notNull(),
    endDate: date("end_date", { mode: "string" }).notNull(),
    /** "morning" / "afternoon" = half day, only allowed when startDate = endDate. */
    period: leavePeriod("period").notNull().default("full"),
    days: numeric("days", { precision: 5, scale: 1, mode: "number" }).notNull(),
    reason: text("reason"),
    status: leaveStatus("status").notNull().default("pending"),
    decidedById: uuid("decided_by_id").references(() => employees.id, { onDelete: "set null" }),
    decidedAt: timestamp("decided_at", { withTimezone: true }),
    decisionNote: text("decision_note"),
    createdAt: createdAt(),
  },
  (t) => [
    index("leave_requests_business_status_idx").on(t.businessId, t.status),
    index("leave_requests_employee_start_idx").on(t.employeeId, t.startDate),
    check("leave_requests_dates_ordered", sql`${t.endDate} >= ${t.startDate}`),
    check("leave_requests_days_positive", sql`${t.days} > 0`),
  ],
);

export const attendance = pgTable(
  "attendance",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    businessId: uuid("business_id")
      .notNull()
      .references(() => businesses.id, { onDelete: "cascade" }),
    employeeId: uuid("employee_id")
      .notNull()
      .references(() => employees.id, { onDelete: "cascade" }),
    branchId: uuid("branch_id").references(() => branches.id, { onDelete: "set null" }),
    /** Local calendar date in the business timezone. */
    workDate: date("work_date", { mode: "string" }).notNull(),
    checkInAt: timestamp("check_in_at", { withTimezone: true }).notNull(),
    checkInLat: doublePrecision("check_in_lat"),
    checkInLng: doublePrecision("check_in_lng"),
    checkInDistanceM: integer("check_in_distance_m"),
    checkOutAt: timestamp("check_out_at", { withTimezone: true }),
    checkOutLat: doublePrecision("check_out_lat"),
    checkOutLng: doublePrecision("check_out_lng"),
    checkOutDistanceM: integer("check_out_distance_m"),
    lateMinutes: integer("late_minutes").notNull().default(0),
    earlyLeaveMinutes: integer("early_leave_minutes").notNull().default(0),
  },
  (t) => [
    uniqueIndex("attendance_employee_date_uq").on(t.employeeId, t.workDate),
    index("attendance_business_date_idx").on(t.businessId, t.workDate),
  ],
);

export type Business = typeof businesses.$inferSelect;
export type Branch = typeof branches.$inferSelect;
export type Employee = typeof employees.$inferSelect;
export type EmployeeRole = (typeof employeeRole.enumValues)[number];
export type LeaveType = typeof leaveTypes.$inferSelect;
export type LeaveRequest = typeof leaveRequests.$inferSelect;
export type LeavePeriod = (typeof leavePeriod.enumValues)[number];
export type LeaveStatus = (typeof leaveStatus.enumValues)[number];
export type Attendance = typeof attendance.$inferSelect;
