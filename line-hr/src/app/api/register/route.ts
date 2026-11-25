import { z } from "zod";
import { getDb } from "@/db";
import { jsonError, parseJson, unauthorized } from "@/lib/api";
import { getSessionLineUserId } from "@/lib/auth";
import { linkLineAccount } from "@/lib/services/employees";

const Body = z.object({ inviteCode: z.string().trim().min(4, { error: "กรุณากรอกรหัสเชิญ" }).max(32) });

/** Links the logged-in LINE account to an employee record using the invite code from the admin. */
export async function POST(req: Request) {
  const lineUserId = await getSessionLineUserId();
  if (!lineUserId) return unauthorized();

  const { data, error } = await parseJson(req, Body);
  if (error) return error;

  const result = await linkLineAccount(getDb(), { inviteCode: data.inviteCode, lineUserId });
  if (!result.ok) {
    return result.code === "already_linked"
      ? jsonError(409, "already_linked", "บัญชี LINE นี้ลงทะเบียนไว้แล้ว")
      : jsonError(400, "invalid_code", "รหัสเชิญไม่ถูกต้อง หรือถูกใช้ไปแล้ว");
  }
  return Response.json({ ok: true, name: result.employee.name });
}
