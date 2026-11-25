"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { LiffGate, LiffHeader } from "@/components/liff/liff-gate";
import { useLiff } from "@/components/liff/liff-provider";
import { buttonClass, Card, Field, inputClass, Notice, Spinner } from "@/components/ui";
import { apiFetch, errorMessage } from "@/lib/client-api";

export default function RegisterPage() {
  return (
    <LiffGate requireEmployee={false}>
      <Register />
    </LiffGate>
  );
}

function Register() {
  const { employee, profile, refresh } = useLiff();
  const router = useRouter();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (employee) {
    return (
      <Card className="mt-10 space-y-3 text-center">
        <p className="text-lg font-semibold">ลงทะเบียนแล้ว ✅</p>
        <p className="text-sm text-slate-600">บัญชี LINE นี้ผูกกับ {employee.name}</p>
        <Link href="/liff" className={buttonClass("primary")}>
          ไปหน้าหลัก
        </Link>
      </Card>
    );
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/register", { json: { inviteCode: code } });
      await refresh();
      router.replace("/liff");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div>
      <LiffHeader title="ลงทะเบียนพนักงาน" back={false} />
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <p className="text-sm text-slate-600">
            สวัสดีคุณ{profile?.displayName ?? ""} กรอกรหัสเชิญ 8 หลักที่ได้รับจากแอดมิน เพื่อผูกบัญชี LINE นี้กับข้อมูลพนักงานของคุณ
          </p>
          <Field label="รหัสเชิญ">
            <input
              className={`${inputClass} text-center font-mono text-2xl tracking-[0.3em] uppercase`}
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              autoCapitalize="characters"
              autoComplete="off"
              maxLength={12}
              placeholder="XXXXXXXX"
              required
            />
          </Field>
          {error && <Notice>{error}</Notice>}
          <button type="submit" className={buttonClass("primary", "lg", "w-full")} disabled={busy || code.length < 6}>
            {busy && <Spinner />} ยืนยัน
          </button>
        </form>
      </Card>
    </div>
  );
}
