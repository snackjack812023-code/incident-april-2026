"use client";

import { IS_DEV_LOGIN, useLiff } from "./liff-provider";

const DEV_USERS = ["U_dev_admin", "U_dev_manager", "U_dev_employee", "U_dev_wipa"];

/** Local testing aid: switch between the seeded demo users. Hidden when a LIFF ID is configured. */
export function DevBanner() {
  const { devUser } = useLiff();
  if (!IS_DEV_LOGIN) return null;
  return (
    <div data-dev-banner className="mt-10 rounded-xl border border-dashed border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
      <p className="font-semibold">โหมดทดสอบ (ไม่ได้ตั้ง NEXT_PUBLIC_LIFF_ID) — ผู้ใช้: {devUser ?? "…"}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {DEV_USERS.map((id) => (
          <a key={id} href={`?as=${id}`} className="rounded-md bg-white px-2 py-1 ring-1 ring-amber-200">
            {id.replace("U_dev_", "")}
          </a>
        ))}
      </div>
    </div>
  );
}
