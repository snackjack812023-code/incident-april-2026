// Read at call time (not import time) so tests and scripts can set process.env first.
export function serverEnv() {
  return {
    lineChannelSecret: process.env.LINE_CHANNEL_SECRET ?? "",
    lineChannelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN ?? "",
    lineLoginChannelId: process.env.LINE_LOGIN_CHANNEL_ID ?? "",
    /** Optional override for the Messaging API host (local mock servers). */
    lineApiBaseUrl: process.env.LINE_API_BASE_URL || undefined,
    sessionSecret: process.env.SESSION_SECRET ?? "",
    /** Public https URL of this app, e.g. https://line-hr.vercel.app (used for links inside LINE messages). */
    appUrl: (process.env.APP_URL ?? "").replace(/\/+$/, ""),
    liffId: process.env.NEXT_PUBLIC_LIFF_ID ?? "",
    /** Local-only login without LINE. Never active in production builds. */
    allowDevLogin: process.env.NODE_ENV !== "production" && process.env.ALLOW_DEV_LOGIN === "true",
  };
}
