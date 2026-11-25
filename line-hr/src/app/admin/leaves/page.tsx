import Link from "next/link";
import { Suspense } from "react";
import { ContentSkeleton } from "@/components/admin/skeleton";
import { getDb } from "@/db";
import type { LeaveStatus } from "@/db/schema";
import { LeaveCard } from "@/components/admin/leave-card";
import { requireStaff } from "@/lib/auth";
import { STATUS_LABELS } from "@/lib/labels";
import { countLeavesByStatus, listLeaves } from "@/lib/services/leaves";

const TABS: Array<LeaveStatus | "all"> = ["pending", "approved", "rejected", "cancelled", "all"];

export default function AdminLeavesPage({ searchParams }: PageProps<"/admin/leaves">) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">คำขอลา</h1>
      <Suspense fallback={<ContentSkeleton />}>
        <Leaves searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function Leaves({ searchParams }: Pick<PageProps<"/admin/leaves">, "searchParams">) {
  const me = await requireStaff("/admin/leaves");
  const requested = (await searchParams).status;
  const tab = TABS.find((t) => t === requested) ?? "pending";

  const db = getDb();
  const [counts, leaves] = await Promise.all([
    countLeavesByStatus(db, me.businessId),
    listLeaves(db, me.businessId, { status: tab === "all" ? undefined : tab }),
  ]);
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-4">
      <div className="flex gap-1 overflow-x-auto">
        {TABS.map((t) => (
          <Link
            key={t}
            href={t === "pending" ? "/admin/leaves" : `/admin/leaves?status=${t}`}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium ring-1 ${
              t === tab ? "bg-slate-900 text-white ring-slate-900" : "bg-white text-slate-600 ring-slate-200"
            }`}
          >
            {t === "all" ? "ทั้งหมด" : STATUS_LABELS[t]} ({t === "all" ? total : counts[t]})
          </Link>
        ))}
      </div>
      {leaves.length === 0 ? (
        <p className="rounded-2xl bg-white p-8 text-center text-slate-500 ring-1 ring-slate-200">ไม่มีรายการ</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {leaves.map((leave) => (
            <LeaveCard key={leave.id} leave={leave} timezone={me.business.timezone} />
          ))}
        </div>
      )}
    </div>
  );
}
