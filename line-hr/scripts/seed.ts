/**
 * Creates the first business, its main branch, default leave types and an admin invite code.
 *
 *   npm run db:seed -- --business "ร้านของฉัน" --admin "ชื่อเจ้าของ"
 *   npm run db:seed -- --demo        # local testing: linked demo users + sample data (dev login)
 */
import { parseArgs } from "node:util";
import { drizzle } from "drizzle-orm/node-postgres";
import { eq } from "drizzle-orm";
import { Pool } from "pg";
import * as schema from "../src/db/schema";
import { checkIn } from "../src/lib/services/attendance";
import { createEmployee, findEmployeeByLineUserId, linkLineAccount } from "../src/lib/services/employees";
import { decideLeave, getLeaveTypes, submitLeave } from "../src/lib/services/leaves";
import { createBusinessWithDefaults } from "../src/lib/services/setup";
import { addDays, zonedParts } from "../src/lib/dates";
import type { LineMessenger } from "../src/lib/line/messenger";

for (const file of [".env.local", ".env"]) {
  try {
    process.loadEnvFile(file);
  } catch {
    // optional
  }
}

const { values } = parseArgs({
  options: {
    business: { type: "string", default: "ร้านตัวอย่าง" },
    admin: { type: "string", default: "แอดมิน" },
    demo: { type: "boolean", default: false },
  },
});

const silent: LineMessenger = { reply: async () => {}, push: async () => {}, multicast: async () => {} };

async function main() {
  if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL is not set (put it in .env.local)");
  const pool = new Pool({ connectionString: process.env.DATABASE_URL });
  const db = drizzle(pool, { schema });

  const { business, branch, admin } = await createBusinessWithDefaults(db, {
    businessName: values.business!,
    adminName: values.admin!,
  });
  console.log(`\n✔ สร้างธุรกิจ "${business.name}" (สาขา: ${branch.name})`);

  if (!values.demo) {
    console.log(`\nรหัสเชิญของแอดมิน (${admin.name}):  ${admin.inviteCode}`);
    console.log("เปิด LIFF หน้า /register ใน LINE แล้วกรอกรหัสนี้ เพื่อผูกบัญชี LINE ของคุณเป็นแอดมิน\n");
    await pool.end();
    return;
  }

  // Demo data for local development with ALLOW_DEV_LOGIN=true (no LINE needed).
  const link = async (inviteCode: string, lineUserId: string) => {
    const result = await linkLineAccount(db, { inviteCode, lineUserId, displayName: null });
    if (!result.ok) throw new Error(`link ${lineUserId}: ${result.code}`);
    return result.employee;
  };
  await db
    .update(schema.branches)
    .set({ latitude: 13.7563, longitude: 100.5018, radiusMeters: 300, lateGraceMinutes: 5 })
    .where(eq(schema.branches.id, branch.id));

  const adminEmp = await link(admin.inviteCode!, "U_dev_admin");
  const people = [
    { name: "สมชาย ขยันดี", position: "หัวหน้ากะ", role: "manager" as const, line: "U_dev_manager" },
    { name: "สมหญิง ใจดี", position: "พนักงานขาย", role: "employee" as const, line: "U_dev_employee" },
    { name: "วิภา สดใส", position: "แคชเชียร์", role: "employee" as const, line: "U_dev_wipa" },
    { name: "อนุชา มั่นคง", position: "พนักงานคลัง", role: "employee" as const, line: null },
  ];
  const linked = new Map<string, Awaited<ReturnType<typeof link>>>();
  for (const p of people) {
    const emp = await createEmployee(db, business.id, { name: p.name, position: p.position, role: p.role });
    if (p.line) linked.set(p.line, await link(emp.inviteCode!, p.line));
    else console.log(`  ${p.name} ยังไม่ผูก LINE — รหัสเชิญ ${emp.inviteCode}`);
  }

  const today = zonedParts(new Date(), business.timezone).date;
  const nextWorkday = (from: string, skip = 0) => {
    let d = from;
    let found = -1;
    while (true) {
      d = addDays(d, 1);
      const wd = new Date(`${d}T00:00:00Z`).getUTCDay();
      if (business.workDays.includes(wd) && ++found === skip) return d;
    }
  };
  const types = await getLeaveTypes(db, business.id);
  const type = (name: string) => types.find((t) => t.name === name)!.id;

  const employee = linked.get("U_dev_employee")!;
  const wipa = linked.get("U_dev_wipa")!;
  const d1 = nextWorkday(today, 2);
  await submitLeave({ db, line: silent }, employee, {
    leaveTypeId: type("ลาพักร้อน"),
    startDate: d1,
    endDate: nextWorkday(d1, 0),
    period: "full",
    reason: "พาครอบครัวไปเที่ยว",
  });
  await submitLeave({ db, line: silent }, wipa, {
    leaveTypeId: type("ลากิจ"),
    startDate: nextWorkday(today, 4),
    endDate: nextWorkday(today, 4),
    period: "morning",
    reason: "ไปทำธุระที่อำเภอ",
  });
  const approved = await submitLeave({ db, line: silent }, wipa, {
    leaveTypeId: type("ลาป่วย"),
    startDate: nextWorkday(today, 6),
    endDate: nextWorkday(today, 6),
    period: "full",
    reason: "นัดหมอฟัน",
  });
  await decideLeave({ db, line: silent }, adminEmp, { leaveId: approved.id, decision: "approve" });

  // Today's check-ins, so the dashboard isn't empty.
  const office = { latitude: 13.7563, longitude: 100.5018 };
  const at = (hhmm: string) => new Date(`${today}T${hhmm}:00+07:00`);
  await checkIn(db, (await findEmployeeByLineUserId(db, "U_dev_manager"))!, office, at("08:52"));
  await checkIn(db, (await findEmployeeByLineUserId(db, "U_dev_employee"))!, office, at("09:17"));

  console.log("\n✔ สร้างข้อมูลตัวอย่างแล้ว ทดลองใช้แบบไม่ต้องมี LINE (ต้องตั้ง ALLOW_DEV_LOGIN=true):");
  console.log("  แอดมิน:   http://localhost:3000/liff/login?next=/admin&as=U_dev_admin");
  console.log("  พนักงาน:  http://localhost:3000/liff?as=U_dev_employee\n");
  await pool.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
