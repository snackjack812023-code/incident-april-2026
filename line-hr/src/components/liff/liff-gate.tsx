"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { buttonClass, Card, Spinner } from "@/components/ui";
import { useLiff } from "./liff-provider";

/** Shows loading / error / "please register" states, and renders children only for linked employees. */
export function LiffGate({ children, requireEmployee = true }: { children: ReactNode; requireEmployee?: boolean }) {
  const { status, error, employee, refresh } = useLiff();

  if (status === "loading") {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-slate-500">
        <Spinner className="size-8 text-line" />
        <p>กำลังเชื่อมต่อ LINE…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <Card className="mt-10 space-y-3 text-center">
        <p className="font-semibold">เชื่อมต่อไม่สำเร็จ</p>
        <p className="text-sm text-slate-600">{error}</p>
        <button type="button" className={buttonClass("secondary")} onClick={() => void refresh()}>
          ลองใหม่
        </button>
      </Card>
    );
  }

  if (requireEmployee && !employee) {
    return (
      <Card className="mt-10 space-y-3 text-center">
        <p className="text-lg font-semibold">ยังไม่ได้ลงทะเบียน</p>
        <p className="text-sm text-slate-600">กรุณาลงทะเบียนด้วยรหัสเชิญที่ได้รับจากแอดมินก่อนใช้งาน</p>
        <Link href="/liff/register" className={buttonClass("primary")}>
          ลงทะเบียน
        </Link>
      </Card>
    );
  }

  return <>{children}</>;
}

export function LiffHeader({ title, back = true }: { title: string; back?: boolean }) {
  return (
    <div className="mb-5 flex items-center gap-2">
      {back && (
        <Link href="/liff" aria-label="กลับ" className="-ml-2 rounded-full p-2 text-slate-500 hover:bg-slate-200">
          <svg viewBox="0 0 20 20" fill="currentColor" className="size-5">
            <path
              fillRule="evenodd"
              d="M12.79 5.23a.75.75 0 0 1-.02 1.06L8.83 10l3.94 3.71a.75.75 0 1 1-1.04 1.08l-4.5-4.25a.75.75 0 0 1 0-1.08l4.5-4.25a.75.75 0 0 1 1.06.02Z"
              clipRule="evenodd"
            />
          </svg>
        </Link>
      )}
      <h1 className="text-xl font-bold">{title}</h1>
    </div>
  );
}
