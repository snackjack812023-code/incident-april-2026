import { getDb } from "@/db";
import { jsonError, unauthorized } from "@/lib/api";
import { getCurrentEmployee } from "@/lib/auth";
import { cancelLeave } from "@/lib/services/leaves";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(_req: Request, ctx: RouteContext<"/api/leaves/[id]/cancel">) {
  const me = await getCurrentEmployee();
  if (!me) return unauthorized();

  const { id } = await ctx.params;
  if (!UUID.test(id) || !(await cancelLeave(getDb(), me, id))) {
    return jsonError(409, "not_cancellable", "ยกเลิกไม่ได้ (คำขอนี้ได้รับการพิจารณาไปแล้ว)");
  }
  return Response.json({ ok: true });
}
