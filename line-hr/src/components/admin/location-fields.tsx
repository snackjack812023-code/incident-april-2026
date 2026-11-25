"use client";

import { useState } from "react";
import { Field, inputClass } from "@/components/ui";

/** Latitude / longitude inputs with a "use my current location" helper for setting up a branch on site. */
export function LocationFields({ latitude, longitude }: { latitude: number | null; longitude: number | null }) {
  const [lat, setLat] = useState(latitude?.toString() ?? "");
  const [lng, setLng] = useState(longitude?.toString() ?? "");
  const [status, setStatus] = useState<string | null>(null);

  function useCurrentLocation() {
    if (!("geolocation" in navigator)) {
      setStatus("เบราว์เซอร์นี้ไม่รองรับการระบุตำแหน่ง");
      return;
    }
    setStatus("กำลังระบุตำแหน่ง…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLng(pos.coords.longitude.toFixed(6));
        setStatus(`ได้ตำแหน่งแล้ว (คลาดเคลื่อน ~${Math.round(pos.coords.accuracy)} ม.) อย่าลืมกดบันทึก`);
      },
      () => setStatus("ระบุตำแหน่งไม่สำเร็จ กรุณาอนุญาตการเข้าถึงตำแหน่ง"),
      { enableHighAccuracy: true, timeout: 15_000 },
    );
  }

  return (
    <div className="space-y-2 sm:col-span-2">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="ละติจูด">
          <input name="latitude" className={inputClass} value={lat} onChange={(e) => setLat(e.target.value)} inputMode="decimal" placeholder="13.756300" />
        </Field>
        <Field label="ลองจิจูด">
          <input name="longitude" className={inputClass} value={lng} onChange={(e) => setLng(e.target.value)} inputMode="decimal" placeholder="100.501800" />
        </Field>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <button type="button" onClick={useCurrentLocation} className="font-medium text-line-dark hover:underline">
          📍 ใช้ตำแหน่งปัจจุบันของฉัน
        </button>
        {status && <span className="text-slate-500">{status}</span>}
        {!lat && !lng && <span className="text-slate-500">เว้นว่าง = เช็คชื่อได้จากทุกที่</span>}
      </div>
    </div>
  );
}
