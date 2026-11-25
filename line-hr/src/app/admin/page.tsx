import Link from "next/link";
import { Suspense } from "react";
import { ContentSkeleton } from "@/components/admin/skeleton";
import { getDb } from "@/db";
import { LeaveCard } from "@/components/admin/leave-card";
import { getDashboard } from "@/lib/services/dashboard";
import { requireStaff } from "@/lib/auth";
import { formatThaiDate, zonedParts } from "@/lib/dates";

const TILE_TONES = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  violet: "bg-violet-50 text-violet-700 ring-violet-100",
  amber: "bg-amber-50 text-amber-700 ring-amber-100",
  rose: "bg-rose-50 text-rose-700 ring-rose-100",
};

function Tile({ label, value, tone, href }: { label: string; value: number; tone: keyof typeof TILE_TONES; href: string }) {
  return (
    <Link href={href} className={`rounded-2xl p-4 ring-1 transition hover:brightness-95 ${TILE_TONES[tone]}`}>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="mt-1 text-3xl font-bold">{value}</p>
    </Link>
  );
}

export default function AdminHomePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">ภาพรวมวันนี้</h1>
      <Suspense fallback={<ContentSkeleton tiles rows={2} />}>
        <Dashboard />
      </Suspense>
    </div>
  );
}

async function Dashboard() {
  const me = await requireStaff("/admin");
  const today = zonedParts(new Date(), me.business.timezone).date;
  const data = await getDashboard(getDb(), me.businessId, today);

  return (
    <div className="space-y-6">
      <p className="-mt-4 text-sm text-slate-500">{formatThaiDate(today, { weekday: true })}</p>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile label="พนักงานทั้งหมด" value={data.totalEmployees} tone="green" href="/admin/employees" />
        <Tile label="มาทำงานวันนี้" value={data.checkedIn} tone="violet" href="/admin/attendance" />
        <Tile label="ลาวันนี้" value={data.onLeave} tone="amber" href="/admin/attendance" />
        <Tile label="มาสาย" value={data.late} tone="rose" href="/admin/attendance" />
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            รออนุมัติ{" "}
            {data.pendingLeaves > 0 && (
              <span className="ml-1 rounded-full bg-rose-500 px-2 py-0.5 text-sm text-white">{data.pendingLeaves}</span>
            )}
          </h2>
          <Link href="/admin/leaves" className="text-sm font-medium text-line-dark hover:underline">
            ดูทั้งหมด →
          </Link>
        </div>
        {data.recentPending.length === 0 ? (
          <p className="rounded-2xl bg-white p-6 text-center text-slate-500 ring-1 ring-slate-200">ไม่มีคำขอลาที่รออนุมัติ 🎉</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {data.recentPending.map((leave) => (
              <LeaveCard key={leave.id} leave={leave} timezone={me.business.timezone} compact />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
