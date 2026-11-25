import { Suspense } from "react";
import { getDb } from "@/db";
import { ContentSkeleton } from "@/components/admin/skeleton";
import {
  createEmployeeAction,
  resetLineLinkAction,
  setEmployeeActiveAction,
  updateEmployeeAction,
} from "@/app/admin/actions";
import { ActionForm, SubmitButton } from "@/components/admin/action-form";
import { Card, Field, inputClass, Pill } from "@/components/ui";
import type { Branch, EmployeeRole } from "@/db/schema";
import { requireStaff } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/labels";
import { listBranches, listEmployees } from "@/lib/services/employees";
import { liffUrl } from "@/lib/urls";

const ROLES: EmployeeRole[] = ["employee", "manager", "admin"];

function EmployeeFields({
  branches,
  defaults,
}: {
  branches: Branch[];
  defaults?: { name: string; position: string | null; role: EmployeeRole; branchId: string | null };
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="ชื่อ-นามสกุล">
        <input name="name" className={inputClass} defaultValue={defaults?.name} required maxLength={100} />
      </Field>
      <Field label="ตำแหน่งงาน">
        <input name="position" className={inputClass} defaultValue={defaults?.position ?? ""} placeholder="เช่น พนักงานขาย" maxLength={100} />
      </Field>
      <Field label="สิทธิ์ในระบบ" hint="หัวหน้างาน/แอดมิน อนุมัติการลาได้ · แอดมินจัดการพนักงานและตั้งค่าได้">
        <select name="role" className={inputClass} defaultValue={defaults?.role ?? "employee"}>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABELS[r]}
            </option>
          ))}
        </select>
      </Field>
      <Field label="สาขา">
        <select name="branchId" className={inputClass} defaultValue={defaults?.branchId ?? branches[0]?.id ?? ""}>
          {branches.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
      </Field>
    </div>
  );
}

export default function AdminEmployeesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">พนักงาน</h1>
      <Suspense fallback={<ContentSkeleton />}>
        <Employees />
      </Suspense>
    </div>
  );
}

async function Employees() {
  const me = await requireStaff("/admin/employees");
  const isAdmin = me.role === "admin";
  const db = getDb();
  const [people, branches] = await Promise.all([listEmployees(db, me.businessId), listBranches(db, me.businessId)]);
  const registerUrl = liffUrl("/register");

  return (
    <div className="space-y-6">
      {isAdmin && (
        <Card>
          <details>
            <summary className="cursor-pointer font-semibold">+ เพิ่มพนักงาน</summary>
            <ActionForm action={createEmployeeAction} className="mt-4 space-y-3">
              <EmployeeFields branches={branches} />
              <SubmitButton>เพิ่มและสร้างรหัสเชิญ</SubmitButton>
            </ActionForm>
          </details>
        </Card>
      )}

      <Card className="space-y-1 bg-sky-50 text-sm text-sky-900 ring-sky-100">
        <p className="font-semibold">วิธีให้พนักงานลงทะเบียน</p>
        <p>
          ส่งลิงก์ {registerUrl ? <code className="break-all rounded bg-white px-1">{registerUrl}</code> : "หน้าลงทะเบียน (LIFF /register)"} ให้พนักงานเปิดใน LINE
          แล้วกรอกรหัสเชิญ 8 หลักของแต่ละคน (ใช้ได้ครั้งเดียว)
        </p>
      </Card>

      <div className="space-y-3">
        {people.map((p) => (
          <Card key={p.id} className={`space-y-3 ${p.active ? "" : "opacity-60"}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                {p.linePictureUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element -- LINE profile CDN
                  <img src={p.linePictureUrl} alt="" className="size-10 rounded-full object-cover" />
                ) : (
                  <div className="flex size-10 items-center justify-center rounded-full bg-slate-200 font-semibold text-slate-600">
                    {p.name.slice(0, 1)}
                  </div>
                )}
                <div>
                  <p className="font-semibold">
                    {p.name} {p.id === me.id && <span className="text-xs text-slate-400">(คุณ)</span>}
                  </p>
                  <p className="text-sm text-slate-500">
                    {[p.position, p.branchName].filter(Boolean).join(" · ") || "—"}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <Pill tone={p.role === "employee" ? "gray" : p.role === "manager" ? "blue" : "violet"}>{ROLE_LABELS[p.role]}</Pill>
                {!p.active && <Pill tone="red">ปิดใช้งาน</Pill>}
                {p.lineUserId ? (
                  <Pill tone="green">LINE: {p.lineDisplayName ?? "เชื่อมแล้ว"}</Pill>
                ) : (
                  <Pill tone="amber">ยังไม่ผูก LINE</Pill>
                )}
              </div>
            </div>

            {!p.lineUserId && p.inviteCode && (
              <div className="flex items-center gap-3 rounded-xl bg-amber-50 px-3 py-2 text-sm">
                <span className="text-amber-800">รหัสเชิญ</span>
                <span className="font-mono text-lg font-bold tracking-widest text-amber-900">{p.inviteCode}</span>
              </div>
            )}

            {isAdmin && (
              <details>
                <summary className="cursor-pointer text-sm font-medium text-slate-600">แก้ไข</summary>
                <div className="mt-3 space-y-4">
                  <ActionForm action={updateEmployeeAction} className="space-y-3">
                    <input type="hidden" name="id" value={p.id} />
                    <EmployeeFields branches={branches} defaults={p} />
                    <SubmitButton size="sm">บันทึก</SubmitButton>
                  </ActionForm>
                  {p.id !== me.id && (
                    <div className="flex flex-wrap gap-4 border-t border-slate-100 pt-3">
                      <ActionForm action={resetLineLinkAction} className="space-y-1">
                        <input type="hidden" name="id" value={p.id} />
                        <SubmitButton variant="secondary" size="sm">
                          {p.lineUserId ? "ยกเลิกการผูก LINE + ออกรหัสใหม่" : "ออกรหัสเชิญใหม่"}
                        </SubmitButton>
                      </ActionForm>
                      <ActionForm action={setEmployeeActiveAction} className="space-y-1">
                        <input type="hidden" name="id" value={p.id} />
                        <input type="hidden" name="active" value={String(!p.active)} />
                        <SubmitButton variant={p.active ? "reject" : "secondary"} size="sm">
                          {p.active ? "ปิดใช้งาน" : "เปิดใช้งาน"}
                        </SubmitButton>
                      </ActionForm>
                    </div>
                  )}
                </div>
              </details>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
