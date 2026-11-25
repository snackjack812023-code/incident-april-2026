/** Postgres SQLSTATE of an error, looking through wrappers such as DrizzleQueryError.cause. */
export function pgErrorCode(err: unknown): string | undefined {
  let current: unknown = err;
  for (let depth = 0; current && depth < 5; depth++) {
    const code = (current as { code?: unknown }).code;
    if (typeof code === "string") return code;
    current = (current as { cause?: unknown }).cause;
  }
  return undefined;
}

/** An expected, user-facing failure. `message` is shown to the user (Thai). */
export class AppError<Code extends string = string> extends Error {
  constructor(
    readonly code: Code,
    message: string,
    readonly status = 400,
  ) {
    super(message);
    this.name = "AppError";
  }
}
