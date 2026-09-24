"use client";

import { X } from "lucide-react";
import { ReactNode, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
  /** Wider variant for content like a diff or a full-screen editor. */
  size?: "sm" | "md" | "lg" | "xl";
  /** Session re-auth must not be escapable — dismissing it solves nothing. */
  dismissible?: boolean;
}

const SIZES = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-5xl",
};

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  dismissible = true,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && dismissible) onClose();
      if (event.key !== "Tab" || !panelRef.current) return;

      // Keep focus inside the dialog so keyboard users can't tab behind it.
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const timer = window.setTimeout(() => {
      panelRef.current?.querySelector<HTMLElement>("input, textarea, button")?.focus();
    }, 30);

    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      window.clearTimeout(timer);
      document.body.style.overflow = overflow;
      previouslyFocused?.focus?.();
    };
  }, [open, onClose, dismissible]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[90] flex items-end justify-center p-0 sm:items-center sm:p-4">
      <div
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={dismissible ? onClose : undefined}
        aria-hidden
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "relative flex max-h-[90vh] w-full flex-col rounded-t-2xl border border-slate-800 bg-slate-900 shadow-2xl sm:rounded-2xl",
          SIZES[size],
        )}
      >
        <div className="flex items-start gap-4 border-b border-slate-800 px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold text-slate-100">{title}</h2>
            {description && <p className="mt-1 text-sm text-slate-400">{description}</p>}
          </div>
          {dismissible && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {children && <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>}

        {footer && (
          <div className="flex flex-wrap justify-end gap-2 border-t border-slate-800 px-5 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

/** Bottom sheet on phones, centred dialog above — same component, mobile-first. */
export function Sheet(props: ModalProps) {
  return <Modal {...props} />;
}
