"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { LeaveBalances } from "@/components/liff/balances";
import { LiffGate, LiffHeader } from "@/components/liff/liff-gate";
import { useLiff } from "@/components/liff/liff-provider";
import { buttonClass, Card, Field, inputClass, Notice, Spinner, StatusPill } from "@/components/ui";
import type { LeavesResponse } from "@/lib/api-types";
import { apiFetch, errorMessage } from "@/lib/client-api";
import { formatThaiDateRange } from "@/lib/dates";
import { countLeaveDays, formatLeaveDays, PERIOD_LABELS, LEAVE_PERIODS, type LeavePeriod } from "@/lib/leave-rules";

export default function LeavePage() {
  return (
    <LiffGate>
      <LeaveScreen />
    </LiffGate>
  );
}

function LeaveScreen() {
  const [data, setData] = useState<LeavesResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    apiFetch<LeavesResponse>("/api/leaves")
      .then((next) => active && setData(next))
      .catch((err) => active && setLoadError(errorMessage(err)));
    return () => {
      active = false;
    };
  }, [version]);

  const load = useCallback(() => setVersion((v) => v + 1), []);

  return (
    <div className="space-y-5">
      <LiffHeader title="ขอลา" />
      {loadError && <Notice>{loadError}</Notice>}
      {!data ? (
        <div className="flex justify-center py-10 text-line">
          <Spinner className="size-7" />
        </div>
      ) : (
        <>
          <LeaveBalances balances={data.balances} />
          <LeaveForm data={data} onSubmitted={load} />
          <LeaveHistory data={data} onChanged={load} />
        </>
      )}
    </div>
  );
}

function LeaveForm({ data, onSubmitted }: { data: LeavesResponse; onSubmitted: () => void }) {
  const { inClient, closeWindow } = useLiff();
  const [typeId, setTypeId] = useState(data.balances[0]?.leaveTypeId ?? "");
  const [start, setStart] = useState(data.today);
  const [end, setEnd] = useState(data.today);
  const [period, setPeriod] = useState<LeavePeriod>("full");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const effectiveEnd = period === "full" ? end : start;
  const preview = useMemo(
    () => countLeaveDays({ startDate: start, endDate: effectiveEnd, period, workDays: data.workDays }),
    [start, effectiveEnd, period, data.workDays],
  );
  const balance = data.balances.find((b) => b.leaveTypeId === typeId);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/leaves", {
        json: { leaveTypeId: typeId, startDate: start, endDate: effectiveEnd, period, reason },
      });
      setDone(true);
      setReason("");
      onSubmitted();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <Card className="space-y-3 text-center">
        <p className="text-4xl">✅</p>
        <p className="text-lg font-semibold">ส่งคำขอลาเรียบร้อย</p>
        <p className="text-sm text-slate-600">ระบบแจ้งหัวหน้าทาง LINE แล้ว ผลการอนุมัติจะส่งกลับมาในแชทนี้</p>
        <div className="flex justify-center gap-2">
          <button type="button" className={buttonClass("secondary")} onClick={() => setDone(false)}>
            ขอลาเพิ่ม
          </button>
          {inClient && (
            <button type="button" className={buttonClass("primary")} onClick={closeWindow}>
              ปิดหน้าต่าง
            </button>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <form onSubmit={submit} className="space-y-4">
        <Field label="ประเภทการลา">
          <select className={inputClass} value={typeId} onChange={(e) => setTypeId(e.target.value)} required>
            {data.balances.map((b) => (
              <option key={b.leaveTypeId} value={b.leaveTypeId}>
                {b.name}
                {b.remainingDays != null ? ` (เหลือ ${b.remainingDays} วัน)` : ""}
                {b.paid ? "" : " · ไม่รับค่าจ้าง"}
              </option>
            ))}
          </select>
        </Field>

        <div className="grid grid-cols-3 gap-2">
          {LEAVE_PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={`rounded-xl px-2 py-2 text-sm font-medium ring-1 ${
                period === p ? "bg-line/10 text-line-dark ring-line" : "bg-white text-slate-600 ring-slate-300"
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>

        <div className={`grid gap-3 ${period === "full" ? "grid-cols-2" : "grid-cols-1"}`}>
          <Field label={period === "full" ? "ตั้งแต่วันที่" : "วันที่"}>
            <input
              type="date"
              className={inputClass}
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                if (e.target.value > end) setEnd(e.target.value);
              }}
              required
            />
          </Field>
          {period === "full" && (
            <Field label="ถึงวันที่">
              <input
                type="date"
                className={inputClass}
                value={end}
                min={start}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </Field>
          )}
        </div>

        <Field label="เหตุผล">
          <textarea
            className={`${inputClass} min-h-24`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={500}
            placeholder="เช่น ไปหาหมอ, ธุระที่ต่างจังหวัด"
          />
        </Field>

        <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm">
          {preview.ok ? (
            <>
              รวม <b>{formatLeaveDays(preview.days, period)}</b>
              {balance?.remainingDays != null && preview.days > balance.remainingDays && (
                <span className="block text-rose-600">เกินวันลาคงเหลือ ({balance.remainingDays} วัน)</span>
              )}
            </>
          ) : (
            <span className="text-rose-600">{preview.error}</span>
          )}
        </div>

        {error && <Notice>{error}</Notice>}

        <button type="submit" className={buttonClass("primary", "lg", "w-full")} disabled={busy || !preview.ok || !typeId}>
          {busy && <Spinner />} ยืนยันการลา
        </button>
      </form>
    </Card>
  );
}

function LeaveHistory({ data, onChanged }: { data: LeavesResponse; onChanged: () => void }) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function cancel(id: string) {
    if (!window.confirm("ยืนยันยกเลิกคำขอลานี้?")) return;
    setBusyId(id);
    setError(null);
    try {
      await apiFetch(`/api/leaves/${id}/cancel`, { method: "POST" });
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-2">
      <h2 className="font-semibold">ประวัติการลา</h2>
      {error && <Notice>{error}</Notice>}
      {data.leaves.length === 0 && <p className="text-sm text-slate-500">ยังไม่มีคำขอลา</p>}
      {data.leaves.map((l) => (
        <Card key={l.id} className="space-y-1 py-3">
          <div className="flex items-center justify-between gap-2">
            <p className="font-medium">{l.leaveTypeName}</p>
            <StatusPill status={l.status} />
          </div>
          <p className="text-sm text-slate-600">
            {formatThaiDateRange(l.startDate, l.endDate)} · {formatLeaveDays(l.days, l.period)}
          </p>
          {l.reason && <p className="text-sm text-slate-500">เหตุผล: {l.reason}</p>}
          {l.deciderName && l.status !== "pending" && (
            <p className="text-xs text-slate-500">
              โดย {l.deciderName}
              {l.decisionNote ? ` — ${l.decisionNote}` : ""}
            </p>
          )}
          {l.status === "pending" && (
            <button
              type="button"
              className="text-sm font-medium text-rose-600"
              disabled={busyId === l.id}
              onClick={() => void cancel(l.id)}
            >
              {busyId === l.id ? "กำลังยกเลิก…" : "ยกเลิกคำขอ"}
            </button>
          )}
        </Card>
      ))}
    </section>
  );
}
