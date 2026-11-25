"use client";

import Link from "next/link";
import { useEffect } from "react";
import { LiffGate } from "@/components/liff/liff-gate";
import { useLiff } from "@/components/liff/liff-provider";
import { buttonClass, Card, Spinner } from "@/components/ui";
import { safeNextPath } from "@/lib/safe-path";

/** Admin web login: signs in with LINE (LIFF also works in a normal browser), then continues to ?next=. */
export default function LoginPage() {
  return (
    <LiffGate requireEmployee={false}>
      <Continue />
    </LiffGate>
  );
}

function Continue() {
  const { employee } = useLiff();
  const isStaff = employee && employee.role !== "employee";

  useEffect(() => {
    if (isStaff) {
      const next = new URLSearchParams(window.location.search).get("next");
      window.location.replace(safeNextPath(next, "/admin"));
    }
  }, [isStaff]);

  if (isStaff) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center gap-3 text-slate-500">
        <Spinner className="text-line" /> กำลังเข้าสู่หน้าแอดมิน…
      </div>
    );
  }

  return (
    <Card className="mt-10 space-y-3 text-center">
      {employee ? (
        <>
          <p className="text-lg font-semibold">บัญชีนี้ไม่มีสิทธิ์เข้าหน้าแอดมิน</p>
          <p className="text-sm text-slate-600">{employee.name} เป็นพนักงานทั่วไป</p>
          <Link href="/liff" className={buttonClass("primary")}>
            ไปหน้าพนักงาน
          </Link>
        </>
      ) : (
        <>
          <p className="text-lg font-semibold">ยังไม่ได้ลงทะเบียน</p>
          <p className="text-sm text-slate-600">ลงทะเบียนด้วยรหัสเชิญของแอดมินก่อน</p>
          <Link href="/liff/register" className={buttonClass("primary")}>
            ลงทะเบียน
          </Link>
        </>
      )}
    </Card>
  );
}
