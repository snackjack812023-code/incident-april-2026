"use client";

import { useActionState, type ReactNode } from "react";
import { useFormStatus } from "react-dom";
import type { ActionState } from "@/app/admin/actions";
import { buttonClass, Spinner } from "@/components/ui";

type Action = (prev: ActionState, formData: FormData) => Promise<ActionState>;

/** A form bound to a server action that shows the action's success / error message. */
export function ActionForm({
  action,
  children,
  className,
  showSuccess = true,
}: {
  action: Action;
  children: ReactNode;
  className?: string;
  showSuccess?: boolean;
}) {
  const [state, formAction] = useActionState(action, null);
  return (
    <form action={formAction} className={className}>
      {children}
      {state && (!state.ok || showSuccess) && (
        <p role="status" className={`text-sm ${state.ok ? "text-emerald-700" : "text-rose-600"}`}>
          {state.message}
        </p>
      )}
    </form>
  );
}

export function SubmitButton({
  children,
  variant = "primary",
  size = "md",
  className,
  name,
  value,
}: {
  children: ReactNode;
  variant?: Parameters<typeof buttonClass>[0];
  size?: Parameters<typeof buttonClass>[1];
  className?: string;
  name?: string;
  value?: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" name={name} value={value} disabled={pending} className={buttonClass(variant, size, className)}>
      {pending && <Spinner className="size-4" />}
      {children}
    </button>
  );
}
