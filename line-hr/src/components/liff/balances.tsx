import type { LeaveBalanceDto } from "@/lib/api-types";

function fmt(n: number) {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

export function LeaveBalances({ balances }: { balances: LeaveBalanceDto[] }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {balances.map((b) => (
        <div key={b.leaveTypeId} className="rounded-2xl bg-white p-3 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm text-slate-500">{b.name}</p>
          {b.quotaDays == null ? (
            <p className="mt-1 text-lg font-semibold">ไม่จำกัด</p>
          ) : (
            <p className="mt-1">
              <span className="text-2xl font-bold text-slate-900">{fmt(b.remainingDays ?? 0)}</span>
              <span className="text-sm text-slate-500"> / {fmt(b.quotaDays)} วัน</span>
            </p>
          )}
          {b.pendingDays > 0 && <p className="text-xs text-amber-600">รออนุมัติ {fmt(b.pendingDays)} วัน</p>}
        </div>
      ))}
    </div>
  );
}
