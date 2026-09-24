import { InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Inline validation message; also wires aria-invalid for screen readers. */
  error?: string | null;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, error, ...props },
  ref,
) {
  return (
    <>
      <input
        ref={ref}
        aria-invalid={error ? true : undefined}
        className={cn(
          "w-full rounded-lg border bg-slate-900/50 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50",
          error
            ? "border-rose-500/60 focus:border-rose-500"
            : "border-slate-700 focus:border-indigo-500",
          className,
        )}
        {...props}
      />
      {error && <p className="mt-1.5 text-xs text-rose-400">{error}</p>}
    </>
  );
});

export function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium text-slate-300">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1.5 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}
