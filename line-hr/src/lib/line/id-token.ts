import { serverEnv } from "../env";

export type LineIdentity = { userId: string; name: string | null; picture: string | null };

export class IdTokenError extends Error {
  constructor(
    message: string,
    readonly expired = false,
  ) {
    super(message);
    this.name = "IdTokenError";
  }
}

const DEV_USER_ID = /^[A-Za-z0-9_-]{3,64}$/;

/**
 * Verifies a LIFF ID token (liff.getIDToken()) with LINE and returns the user.
 * `dev:<userId>` tokens are accepted only when ALLOW_DEV_LOGIN=true outside production.
 */
export async function verifyLineIdToken(idToken: string): Promise<LineIdentity> {
  const env = serverEnv();

  if (idToken.startsWith("dev:")) {
    const userId = idToken.slice(4);
    if (!env.allowDevLogin) throw new IdTokenError("Dev login is disabled");
    if (!DEV_USER_ID.test(userId)) throw new IdTokenError("Invalid dev user id");
    return { userId, name: `Dev ${userId}`, picture: null };
  }

  if (!env.lineLoginChannelId) throw new Error("LINE_LOGIN_CHANNEL_ID is not set");

  const res = await fetch("https://api.line.me/oauth2/v2.1/verify", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ id_token: idToken, client_id: env.lineLoginChannelId }),
  });
  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;

  if (!res.ok) {
    const description = String(data.error_description ?? data.error ?? `HTTP ${res.status}`);
    throw new IdTokenError(description, /expired/i.test(description));
  }
  if (data.iss !== "https://access.line.me" || data.aud !== env.lineLoginChannelId || typeof data.sub !== "string") {
    throw new IdTokenError("Unexpected ID token claims");
  }
  return {
    userId: data.sub,
    name: typeof data.name === "string" ? data.name : null,
    picture: typeof data.picture === "string" ? data.picture : null,
  };
}
