import { serverEnv } from "./env";

/** Link that opens a LIFF page inside LINE, e.g. liffUrl("/leave"). */
export function liffUrl(path: "/" | `/${string}` = "/"): string | null {
  const { liffId, appUrl } = serverEnv();
  const suffix = path === "/" ? "" : path;
  if (liffId) return `https://liff.line.me/${liffId}${suffix}`;
  return appUrl ? `${appUrl}/liff${suffix}` : null;
}

export function adminUrl(path: "" | `/${string}` = ""): string | null {
  const { appUrl } = serverEnv();
  return appUrl ? `${appUrl}/admin${path}` : null;
}
