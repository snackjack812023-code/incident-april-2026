import { Suspense } from "react";
import { getDb } from "@/db";
import { ContentSkeleton } from "@/components/admin/skeleton";
import { saveBranchAction, saveLeaveTypeAction, updateBusinessAction } from "@/app/admin/actions";
import { ActionForm, SubmitButton } from "@/components/admin/action-form";
import { LocationFields } from "@/components/admin/location-fields";
import { Card, Field, inputClass } from "@/components/ui";
import type { Branch, LeaveType } from "@/db/schema";
import { requireAdmin } from "@/lib/auth";
import { WEEKDAY_LABELS } from "@/lib/labels";
import { listBranches } from "@/lib/services/employees";
import { getLeaveTypes } from "@/lib/services/leaves";
import { getBusiness } from "@/lib/services/setup";

// Monday first, as on a Thai work calendar.
const WEEK_ORDER = [1, 2, 3, 4, 5, 6, 0];

function BranchForm({ branch }: { branch?: Branch }) {
  return (
    <ActionForm action={saveBranchAction} className="space-y-3">
      {branch && <input type="hidden" name="id" value={branch.id} />}
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="ชื่อสาขา">
          <input name="name" className={inputClass} defaultValue={branch?.name} required maxLength={100} />
        </Field>
        <Field label="รัศมีเช็คชื่อ (เมตร)">
          <input name="radiusMeters" type="number" min={20} max={5000} className={inputClass} defaultValue={branch?.radiusMeters ?? 150} />
        </Field>
        <LocationFields latitude={branch?.latitude ?? null} longitude={branch?.longitude ?? null} />
        <Field label="เวลาเข้างาน">
          <input name="workStart" type="time" className={inputClass} defaultValue={branch?.workStart ?? "09:00"} required />
        </Field>
        <Field label="เวลาเลิกงาน">
          <input name="workEnd" type="time" className={inputClass} defaultValue={branch?.workEnd ?? "18:00"} required />
        </Field>
        <Field label="ผ่อนผันมาสาย (นาที)" hint="เช็คอินหลังเวลาเข้างานไม่เกินนี้ ไม่นับว่าสาย">
          <input name="lateGraceMinutes" type="number" min={0} max={240} className={inputClass} defaultValue={branch?.lateGraceMinutes ?? 0} />
        </Field>
      </div>
      <SubmitButton size="sm">{branch ? "บันทึกสาขา" : "เพิ่มสาขา"}</SubmitButton>
    </ActionForm>
  );
}

function LeaveTypeForm({ type }: { type?: LeaveType }) {
  return (
    <ActionForm action={saveLeaveTypeAction} className="space-y-2">
      {type && <input type="hidden" name="id" value={type.id} />}
      <div className="grid items-end gap-3 sm:grid-cols-[2fr_1fr_auto_auto_auto]">
        <Field label="ชื่อประเภท">
          <input name="name" className={inputClass} defaultValue={type?.name} required maxLength={60} />
        </Field>
        <Field label="วัน/ปี" hint="ว่าง = ไม่จำกัด">
          <input name="quotaDays" type="number" step="0.5" min={0} max={366} className={inputClass} defaultValue={type?.quotaDays ?? ""} />
        </Field>
        <label className="flex items-center gap-2 pb-3 text-sm">
          <input type="checkbox" name="paid" defaultChecked={type?.paid ?? true} className="size-4 accent-line" /> ได้รับค่าจ้าง
        </label>
        {type ? (
          <label className="flex items-center gap-2 pb-3 text-sm">
            <input type="checkbox" name="active" defaultChecked={type.active} className="size-4 accent-line" /> เปิดใช้
          </label>
        ) : (
          <span />
        )}
        <div className="pb-1">
          <SubmitButton size="sm" variant={type ? "secondary" : "primary"}>
            {type ? "บันทึก" : "เพิ่ม"}
          </SubmitButton>
        </div>
      </div>
    </ActionForm>
  );
}

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">ตั้งค่า</h1>
      <Suspense fallback={<ContentSkeleton />}>
        <Settings />
      </Suspense>
    </div>
  );
}

async function Settings() {
  const me = await requireAdmin("/admin/settings");
  const db = getDb();
  const [business, branches, leaveTypes] = await Promise.all([
    getBusiness(db, me.businessId),
    listBranches(db, me.businessId),
    getLeaveTypes(db, me.businessId, { includeInactive: true }),
  ]);
  if (!business) return null;

  return (
    <div className="space-y-6">
      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">ธุรกิจ</h2>
        <ActionForm action={updateBusinessAction} className="space-y-3">
          <Field label="ชื่อธุรกิจ / ร้าน">
            <input name="name" className={inputClass} defaultValue={business.name} required maxLength={100} />
          </Field>
          <fieldset className="space-y-1.5">
            <legend className="text-sm font-medium text-slate-700">วันทำงาน (ใช้นับจำนวนวันลา)</legend>
            <div className="flex flex-wrap gap-2">
              {WEEK_ORDER.map((d) => (
                <label key={d} className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-3 py-2 text-sm ring-1 ring-slate-200">
                  <input type="checkbox" name="workDays" value={d} defaultChecked={business.workDays.includes(d)} className="accent-line" />
                  {WEEKDAY_LABELS[d]}
                </label>
              ))}
            </div>
          </fieldset>
          <SubmitButton size="sm">บันทึก</SubmitButton>
        </ActionForm>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">สาขาและเวลาทำงาน</h2>
        {branches.map((branch) => (
          <div key={branch.id} className="border-b border-slate-100 pb-4 last:border-0">
            <BranchForm branch={branch} />
          </div>
        ))}
        <details>
          <summary className="cursor-pointer text-sm font-semibold text-line-dark">+ เพิ่มสาขา</summary>
          <div className="mt-3">
            <BranchForm />
          </div>
        </details>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">ประเภทการลาและโควตา</h2>
        <p className="text-sm text-slate-500">
          ค่าเริ่มต้นอิงขั้นต่ำตามกฎหมายคุ้มครองแรงงาน (ลาป่วยได้รับค่าจ้างไม่เกิน 30 วัน, ลากิจอย่างน้อย 3 วัน,
          พักร้อนอย่างน้อย 6 วันเมื่อทำงานครบ 1 ปี) ปรับได้ตามนโยบายของร้าน
        </p>
        {leaveTypes.map((type) => (
          <div key={type.id} className="border-b border-slate-100 pb-3">
            <LeaveTypeForm type={type} />
          </div>
        ))}
        <details>
          <summary className="cursor-pointer text-sm font-semibold text-line-dark">+ เพิ่มประเภทการลา</summary>
          <div className="mt-3">
            <LeaveTypeForm />
          </div>
        </details>
      </Card>
    </div>
  );
}
