import { createHmac, timingSafeEqual } from "node:crypto";

/** Verifies the x-line-signature header: base64(HMAC-SHA256(channelSecret, rawBody)). */
export function verifyLineSignature(rawBody: string, signature: string, channelSecret: string): boolean {
  if (!signature || !channelSecret) return false;
  const expected = createHmac("sha256", channelSecret).update(rawBody, "utf8").digest();
  const given = Buffer.from(signature, "base64");
  return given.length === expected.length && timingSafeEqual(given, expected);
}

export function signLineBody(rawBody: string, channelSecret: string): string {
  return createHmac("sha256", channelSecret).update(rawBody, "utf8").digest("base64");
}
