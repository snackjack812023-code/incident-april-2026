import { cookies } from "next/headers";
import { z } from "zod";
import { getDb } from "@/db";
import { jsonError, parseJson } from "@/lib/api";
import type { AuthResponse } from "@/lib/api-types";
import { IdTokenError, verifyLineIdToken } from "@/lib/line/id-token";
import { findEmployeeByLineUserId, updateLineProfile } from "@/lib/services/employees";
import { SESSION_COOKIE, sessionCookieOptions, signSession } from "@/lib/session";

const Body = z.object({ idToken: z.string().min(1).max(8192) });

/** Exchanges a LIFF ID token for an httpOnly session cookie. */
export async function POST(req: Request) {
  const { data, error } = await parseJson(req, Body);
  if (error) return error;

  let identity;
  try {
    identity = await verifyLineIdToken(data.idToken);
  } catch (err) {
    if (err instanceof IdTokenError) {
      return jsonError(401, err.expired ? "id_token_expired" : "invalid_id_token", "ยืนยันตัวตนกับ LINE ไม่สำเร็จ");
    }
    throw err;
  }

  (await cookies()).set(SESSION_COOKIE, await signSession(identity.userId), sessionCookieOptions());

  const db = getDb();
  const employee = await findEmployeeByLineUserId(db, identity.userId);
  if (employee && (employee.lineDisplayName !== identity.name || employee.linePictureUrl !== identity.picture)) {
    await updateLineProfile(db, employee.id, { displayName: identity.name, pictureUrl: identity.picture });
  }

  const body: AuthResponse = {
    profile: { displayName: identity.name, pictureUrl: identity.picture },
    employee:
      employee && employee.active
        ? {
            id: employee.id,
            name: employee.name,
            role: employee.role,
            position: employee.position,
            businessName: employee.business.name,
          }
        : null,
  };
  return Response.json(body);
}
