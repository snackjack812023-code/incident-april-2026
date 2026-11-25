"use client";

import { useState } from "react";
import { decideLeaveAction } from "@/app/admin/actions";
import { inputClass } from "@/components/ui";
import { ActionForm, SubmitButton } from "./action-form";

export function DecisionForm({ leaveId, allowNote = true }: { leaveId: string; allowNote?: boolean }) {
  const [withNote, setWithNote] = useState(false);
  return (
    <ActionForm action={decideLeaveAction} className="space-y-2" showSuccess={false}>
      <input type="hidden" name="leaveId" value={leaveId} />
      {withNote && (
        <textarea name="note" className={`${inputClass} min-h-16 text-sm`} placeholder="หมายเหตุถึงพนักงาน (ไม่บังคับ)" maxLength={300} />
      )}
      <div className="flex flex-wrap items-center gap-2">
        <SubmitButton name="decision" value="approve" variant="approve" size="sm">
          อนุมัติ
        </SubmitButton>
        <SubmitButton name="decision" value="reject" variant="reject" size="sm">
          ปฏิเสธ
        </SubmitButton>
        {allowNote && !withNote && (
          <button type="button" className="text-sm text-slate-500 hover:text-slate-800" onClick={() => setWithNote(true)}>
            + หมายเหตุ
          </button>
        )}
      </div>
    </ActionForm>
  );
}
