"use client";

import { useEffect, useState } from "react";
import { LiffGate, LiffHeader } from "@/components/liff/liff-gate";
import { buttonClass, Card, Notice, Spinner } from "@/components/ui";
import type { AttendanceResponse } from "@/lib/api-types";
import { apiFetch, errorMessage } from "@/lib/client-api";
import { formatThaiDate } from "@/lib/dates";

export default function CheckinPage() {
  return (
    <LiffGate>
      <Checkin />
    </LiffGate>
  );
}

function getPosition(): Promise<{ latitude: number; longitude: number }> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("อุปกรณ์นี้ไม่รองรับการระบุตำแหน่ง"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      (err) =>
        reject(
          new Error(
            err.code === err.PERMISSION_DENIED
              ? "กรุณาอนุญาตให้ LINE เข้าถึงตำแหน่ง (Location) แล้วลองอีกครั้ง"
              : "ระบุตำแหน่งไม่สำเร็จ กรุณาลองใหม่ในที่โล่ง",
          ),
        ),
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 0 },
    );
  });
}

function Checkin() {
  const [snap, setSnap] = useState<AttendanceResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<AttendanceResponse>("/api/attendance")
      .then(setSnap)
      .catch((err) => setError(errorMessage(err)));
  }, []);

  async function act(action: "in" | "out") {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const position = snap?.branch?.hasGeofence ? await getPosition() : null;
      const next = await apiFetch<AttendanceResponse>("/api/attendance", { json: { action, ...position } });
      setSnap(next);
      setSuccess(
        action === "in"
          ? `เช็คอินสำเร็จ เวลา ${next.record?.checkInTime} น.`
          : `เช็คเอาท์สำเร็จ เวลา ${next.record?.checkOutTime} น.`,
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!snap) {
    return (
      <div>
        <LiffHeader title="เช็คชื่อ เข้า-ออกงาน" />
        {error ? <Notice>{error}</Notice> : <div className="flex justify-center py-10 text-line"><Spinner className="size-7" /></div>}
      </div>
    );
  }

  const record = snap.record;
  const nextAction = !record ? "in" : !record.checkOutTime ? "out" : null;

  return (
    <div className="space-y-4">
      <LiffHeader title="เช็คชื่อ เข้า-ออกงาน" />

      <Card className="text-center">
        <p className="text-slate-500">{formatThaiDate(snap.date, { weekday: true })}</p>
        <p className="mt-1 text-5xl font-bold tabular-nums tracking-tight">{snap.time}</p>
        {snap.branch ? (
          <p className="mt-2 text-sm text-slate-500">
            {snap.branch.name} · เวลางาน {snap.branch.workStart}–{snap.branch.workEnd} น.
          </p>
        ) : (
          <p className="mt-2 text-sm text-rose-600">ยังไม่ได้กำหนดสาขา กรุณาติดต่อแอดมิน</p>
        )}
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Card className="text-center">
          <p className="text-sm text-slate-500">เข้างาน</p>
          <p className="text-2xl font-semibold tabular-nums">{record?.checkInTime ?? "--:--"}</p>
          {record && record.lateMinutes > 0 && <p className="text-xs text-rose-600">สาย {record.lateMinutes} นาที</p>}
        </Card>
        <Card className="text-center">
          <p className="text-sm text-slate-500">ออกงาน</p>
          <p className="text-2xl font-semibold tabular-nums">{record?.checkOutTime ?? "--:--"}</p>
          {record && record.earlyLeaveMinutes > 0 && (
            <p className="text-xs text-amber-600">ออกก่อน {record.earlyLeaveMinutes} นาที</p>
          )}
        </Card>
      </div>

      {success && <Notice tone="green">{success}</Notice>}
      {error && <Notice>{error}</Notice>}

      {nextAction ? (
        <button
          type="button"
          className={buttonClass(nextAction === "in" ? "primary" : "approve", "lg", "w-full py-5 text-xl")}
          disabled={busy || !snap.branch}
          onClick={() => void act(nextAction)}
        >
          {busy && <Spinner />}
          {nextAction === "in" ? "เช็คอินเข้างาน" : "เช็คเอาท์ออกงาน"}
        </button>
      ) : (
        <Notice tone="green">วันนี้บันทึกเวลาเข้า-ออกครบแล้ว 👍</Notice>
      )}

      {snap.branch?.hasGeofence && (
        <p className="text-center text-xs text-slate-500">
          ต้องอยู่ในรัศมี {snap.branch.radiusMeters} ม. จากสาขา ระบบจะขอใช้ตำแหน่งของคุณตอนกดปุ่ม
        </p>
      )}
    </div>
  );
}
