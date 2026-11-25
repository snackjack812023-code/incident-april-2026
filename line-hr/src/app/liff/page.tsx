"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LeaveBalances } from "@/components/liff/balances";
import { LiffGate } from "@/components/liff/liff-gate";
import { useLiff } from "@/components/liff/liff-provider";
import { Card, Notice, StatusPill } from "@/components/ui";
import type { AttendanceResponse, LeavesResponse } from "@/lib/api-types";
import { apiFetch, errorMessage } from "@/lib/client-api";
import { formatThaiDate, formatThaiDateRange } from "@/lib/dates";
import { ROLE_LABELS } from "@/lib/labels";
import { formatLeaveDays } from "@/lib/leave-rules";

export default function LiffHomePage() {
  return (
    <LiffGate>
      <Home />
    </LiffGate>
  );
}

function Home() {
  const { employee, profile } = useLiff();
  const [leaves, setLeaves] = useState<LeavesResponse | null>(null);
  const [today, setToday] = useState<AttendanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([apiFetch<LeavesResponse>("/api/leaves"), apiFetch<AttendanceResponse>("/api/attendance")])
      .then(([l, a]) => {
        setLeaves(l);
        setToday(a);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  if (!employee) return null;
  const isStaff = employee.role !== "employee";

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        {profile?.pictureUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- LINE profile CDN, any size
          <img src={profile.pictureUrl} alt="" className="size-14 rounded-full object-cover ring-2 ring-white" />
        ) : (
          <div className="flex size-14 items-center justify-center rounded-full bg-line text-xl font-bold text-white">
            {employee.name.slice(0, 1)}
          </div>
        )}
        <div>
          <p className="text-lg font-bold leading-tight">{employee.name}</p>
          <p className="text-sm text-slate-500">
            {employee.position ?? ROLE_LABELS[employee.role]} · {employee.businessName}
          </p>
        </div>
      </div>

      {error && <Notice>{error}</Notice>}

      <Card className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500">{today ? formatThaiDate(today.date, { weekday: true }) : "วันนี้"}</p>
          <p className="font-semibold">
            {!today
              ? "…"
              : !today.record
                ? "ยังไม่ได้เช็คอิน"
                : today.record.checkOutTime
                  ? `เข้า ${today.record.checkInTime} · ออก ${today.record.checkOutTime}`
                  : `เช็คอินแล้ว ${today.record.checkInTime} น.`}
          </p>
          {today?.record && today.record.lateMinutes > 0 && (
            <p className="text-sm text-rose-600">สาย {today.record.lateMinutes} นาที</p>
          )}
        </div>
        <Link href="/liff/checkin" className="rounded-xl bg-line px-4 py-2.5 font-semibold text-white">
          เช็คชื่อ
        </Link>
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Link href="/liff/leave" className="rounded-2xl bg-white p-4 text-center font-semibold shadow-sm ring-1 ring-slate-200">
          <span className="block text-2xl">📝</span>ขอลา
        </Link>
        <Link href="/liff/checkin" className="rounded-2xl bg-white p-4 text-center font-semibold shadow-sm ring-1 ring-slate-200">
          <span className="block text-2xl">📍</span>เข้า-ออกงาน
        </Link>
      </div>

      {isStaff && (
        <a href="/admin" className="block rounded-2xl bg-slate-900 p-4 text-center font-semibold text-white">
          ไปหน้าแอดมิน →
        </a>
      )}

      {leaves && (
        <>
          <section className="space-y-2">
            <h2 className="font-semibold">วันลาคงเหลือปีนี้</h2>
            <LeaveBalances balances={leaves.balances} />
          </section>
          <section className="space-y-2">
            <h2 className="font-semibold">คำขอลาล่าสุด</h2>
            {leaves.leaves.length === 0 && <p className="text-sm text-slate-500">ยังไม่มีคำขอลา</p>}
            {leaves.leaves.slice(0, 3).map((l) => (
              <Card key={l.id} className="flex items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-medium">{l.leaveTypeName}</p>
                  <p className="text-sm text-slate-500">
                    {formatThaiDateRange(l.startDate, l.endDate)} · {formatLeaveDays(l.days, l.period)}
                  </p>
                </div>
                <StatusPill status={l.status} />
              </Card>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
