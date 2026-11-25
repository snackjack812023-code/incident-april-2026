import "server-only";
import type { z } from "zod";
import { AppError } from "./services/errors";

export function jsonError(status: number, code: string, message: string) {
  return Response.json({ error: { code, message } }, { status });
}

export const unauthorized = () => jsonError(401, "unauthorized", "กรุณาเข้าสู่ระบบผ่าน LINE ใหม่อีกครั้ง");

/** Parses a JSON body with a zod schema; returns the data or a 400 response. */
export async function parseJson<T extends z.ZodType>(
  req: Request,
  schema: T,
): Promise<{ data: z.infer<T>; error?: never } | { data?: never; error: Response }> {
  // Only accept real JSON requests (blocks cross-site <form> posts with a text/plain body).
  if (!req.headers.get("content-type")?.includes("application/json")) {
    return { error: jsonError(415, "unsupported_media_type", "ต้องส่งข้อมูลเป็น JSON") };
  }
  const body = await req.json().catch(() => undefined);
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    const first = parsed.error.issues[0];
    return { error: jsonError(400, "invalid_request", first?.message ?? "ข้อมูลไม่ถูกต้อง") };
  }
  return { data: parsed.data };
}

/** Turns expected AppErrors into JSON responses; lets anything else bubble up as a 500. */
export function handleAppError(err: unknown): Response {
  if (err instanceof AppError) return jsonError(err.status, err.code, err.message);
  throw err;
}
