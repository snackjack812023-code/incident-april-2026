import { logoutAction } from "@/app/admin/actions";
import { getCurrentEmployee } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/labels";

/** Reads the session, so it must render inside <Suspense>. */
export async function AdminUser() {
  const me = await getCurrentEmployee();
  if (!me) return null;
  return (
    <div className="flex items-center gap-3">
      <div className="text-right leading-tight">
        <p className="text-sm font-semibold">{me.name}</p>
        <p className="hidden text-xs text-slate-500 sm:block">
          {ROLE_LABELS[me.role]} · {me.business.name}
        </p>
      </div>
      <form action={logoutAction}>
        <button type="submit" className="whitespace-nowrap rounded-lg px-2 py-1 text-xs text-slate-500 ring-1 ring-slate-200 hover:bg-slate-50">
          ออกจากระบบ
        </button>
      </form>
    </div>
  );
}
