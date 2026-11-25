import { Card, Pill, StatusPill } from "@/components/ui";
import { formatThaiDateRange, formatThaiDateTime } from "@/lib/dates";
import { formatLeaveDays } from "@/lib/leave-rules";
import type { LeaveDetail } from "@/lib/services/leaves";
import { DecisionForm } from "./decision-form";

export function LeaveCard({ leave, timezone, compact = false }: { leave: LeaveDetail; timezone: string; compact?: boolean }) {
  return (
    <Card className="space-y-2">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold">{leave.employeeName}</p>
          <p className="text-sm text-slate-600">
            {leave.leaveTypeName} · {formatThaiDateRange(leave.startDate, leave.endDate)} ·{" "}
            {formatLeaveDays(leave.days, leave.period)}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          {!leave.paid && <Pill tone="amber">ไม่รับค่าจ้าง</Pill>}
          <StatusPill status={leave.status} />
        </div>
      </div>
      {leave.reason && <p className="text-sm text-slate-700">เหตุผล: {leave.reason}</p>}
      {!compact && <p className="text-xs text-slate-400">ส่งเมื่อ {formatThaiDateTime(leave.createdAt, timezone)}</p>}
      {leave.status !== "pending" && leave.deciderName && (
        <p className="text-xs text-slate-500">
          {leave.status === "cancelled" ? "" : `โดย ${leave.deciderName}`}
          {leave.decidedAt ? ` เมื่อ ${formatThaiDateTime(leave.decidedAt, timezone)}` : ""}
          {leave.decisionNote ? ` — ${leave.decisionNote}` : ""}
        </p>
      )}
      {leave.status === "pending" && <DecisionForm leaveId={leave.id} allowNote={!compact} />}
    </Card>
  );
}
