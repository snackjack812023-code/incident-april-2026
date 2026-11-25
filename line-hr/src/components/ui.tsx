// Small presentational components. No hooks, so they work in both Server and Client Components.
import type { ComponentProps, ReactNode } from "react";
import type { LeaveStatus } from "@/db/schema";
import { STATUS_LABELS } from "@/lib/labels";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function Card({ className, ...props }: ComponentProps<"div">) {
  return <div className={cx("rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200", className)} {...props} />;
}

const BUTTON_VARIANTS = {
  primary: "bg-line text-white hover:bg-line-dark disabled:bg-slate-300",
  secondary: "bg-white text-slate-800 ring-1 ring-slate-300 hover:bg-slate-50",
  approve: "bg-emerald-600 text-white hover:bg-emerald-700",
  reject: "bg-white text-rose-600 ring-1 ring-rose-200 hover:bg-rose-50",
  ghost: "text-slate-600 hover:bg-slate-100",
} as const;

const BUTTON_SIZES = {
  sm: "px-3 py-1.5 text-sm rounded-lg",
  md: "px-4 py-2.5 rounded-xl",
  lg: "px-5 py-3.5 text-lg rounded-2xl",
} as const;

export function buttonClass(
  variant: keyof typeof BUTTON_VARIANTS = "primary",
  size: keyof typeof BUTTON_SIZES = "md",
  className?: string,
) {
  return cx(
    "inline-flex items-center justify-center gap-2 font-semibold transition disabled:cursor-not-allowed disabled:opacity-60",
    BUTTON_VARIANTS[variant],
    BUTTON_SIZES[size],
    className,
  );
}

const STATUS_TONES: Record<LeaveStatus, string> = {
  pending: "bg-amber-50 text-amber-700 ring-amber-200",
  approved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  rejected: "bg-rose-50 text-rose-700 ring-rose-200",
  cancelled: "bg-slate-100 text-slate-500 ring-slate-200",
};

export const TONES = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  amber: "bg-amber-50 text-amber-700 ring-amber-200",
  red: "bg-rose-50 text-rose-700 ring-rose-200",
  blue: "bg-sky-50 text-sky-700 ring-sky-200",
  violet: "bg-violet-50 text-violet-700 ring-violet-200",
  gray: "bg-slate-100 text-slate-600 ring-slate-200",
} as const;

export function Pill({ tone = "gray", children }: { tone?: keyof typeof TONES; children: ReactNode }) {
  return (
    <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1", TONES[tone])}>
      {children}
    </span>
  );
}

export function StatusPill({ status }: { status: LeaveStatus }) {
  return (
    <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1", STATUS_TONES[status])}>
      {STATUS_LABELS[status]}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cx("inline-block size-5 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

export function Notice({ tone = "red", children }: { tone?: "red" | "green" | "amber"; children: ReactNode }) {
  const tones = {
    red: "bg-rose-50 text-rose-700 ring-rose-200",
    green: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    amber: "bg-amber-50 text-amber-800 ring-amber-200",
  };
  return <div className={cx("rounded-xl px-4 py-3 text-sm ring-1", tones[tone])}>{children}</div>;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-base outline-none focus:border-line focus:ring-2 focus:ring-line/20 disabled:bg-slate-100";
