import Link from "next/link";
import { Suspense } from "react";
import { ContentSkeleton } from "@/components/admin/skeleton";
import { getDb } from "@/db";
import { Card, Pill } from "@/components/ui";
import { requireStaff } from "@/lib/auth";
import { addDays, formatThaiDate, formatTime, isValidIsoDate, zonedParts } from "@/lib/dates";
import { DAILY_STATUS_LABELS, type DailyStatus } from "@/lib/labels";
import { PERIOD_LABELS } from "@/lib/leave-rules";
import { getDailyAttendance } from "@/lib/services/attendance";

const STATUS_TONE: Record<DailyStatus, "green" | "red" | "amber" | "gray"> = {
  present: "green",
  late: "red",
  leave: "amber",
  absent: "gray",
};

export default function AdminAttendancePage({ searchParams }: PageProps<"/admin/attendance">) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">ลงเวลาเข้า-ออก</h1>
      <Suspense fallback={<ContentSkeleton rows={2} />}>
        <Attendance searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function Attendance({ searchParams }: Pick<PageProps<"/admin/attendance">, "searchParams">) {
  const me = await requireStaff("/admin/attendance");
  const tz = me.business.timezone;
  const today = zonedParts(new Date(), tz).date;
  const requested = (await searchParams).date;
  const date = typeof requested === "string" && isValidIsoDate(requested) ? requested : today;
  const rows = await getDailyAttendance(getDb(), me.businessId, date);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-lg font-medium text-slate-600">{formatThaiDate(date, { weekday: true })}</p>
        <div className="flex items-center gap-2">
          <Link href={`/admin/attendance?date=${addDays(date, -1)}`} className="rounded-lg bg-white px-3 py-2 text-sm ring-1 ring-slate-200">
            ← วันก่อน
          </Link>
          <form className="flex gap-2">
            <input type="date" name="date" defaultValue={date} className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm" />
            <button className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white">ดู</button>
          </form>
          {date < today && (
            <Link href={`/admin/attendance?date=${addDays(date, 1)}`} className="rounded-lg bg-white px-3 py-2 text-sm ring-1 ring-slate-200">
              วันถัดไป →
            </Link>
          )}
        </div>
      </div>

      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="border-b border-slate-200 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">พนักงาน</th>
              <th className="px-4 py-3 font-medium">สถานะ</th>
              <th className="px-4 py-3 font-medium">เข้างาน</th>
              <th className="px-4 py-3 font-medium">ออกงาน</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="px-4 py-3">
                  <p className="font-medium">{row.name}</p>
                  {row.position && <p className="text-xs text-slate-500">{row.position}</p>}
                </td>
                <td className="px-4 py-3">
                  <Pill tone={STATUS_TONE[row.status]}>{DAILY_STATUS_LABELS[row.status]}</Pill>
                  {row.leave && (
                    <p className="mt-1 text-xs text-slate-500">
                      {row.leave.leaveTypeName}
                      {row.leave.period !== "full" ? ` (${PERIOD_LABELS[row.leave.period]})` : ""}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {row.record ? formatTime(row.record.checkInAt, tz) : "–"}
                  {row.record && row.record.lateMinutes > 0 && (
                    <span className="ml-2 text-xs text-rose-600">สาย {row.record.lateMinutes} น.</span>
                  )}
                  {row.record?.checkInDistanceM != null && (
                    <span className="block text-xs text-slate-400">ห่างสาขา {row.record.checkInDistanceM} ม.</span>
                  )}
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {row.record?.checkOutAt ? formatTime(row.record.checkOutAt, tz) : "–"}
                  {row.record && row.record.earlyLeaveMinutes > 0 && (
                    <span className="ml-2 text-xs text-amber-600">ออกก่อน {row.record.earlyLeaveMinutes} น.</span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  ยังไม่มีพนักงาน
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
