/** Only allow same-site relative redirects ("/admin", not "//evil.com" or "https://…"). */
export function safeNextPath(value: string | null | undefined, fallback: string): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return fallback;
  return value;
}
