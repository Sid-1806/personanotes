"use client";

import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { cn } from "@/lib/utils";

type ToastTone = "success" | "error" | "info";

interface Toast {
  id: number;
  tone: ToastTone;
  message: string;
  /** Destructive actions get an Undo rather than a confirm dialog. */
  action?: { label: string; onClick: () => void };
  duration: number;
}

interface ToastOptions {
  tone?: ToastTone;
  action?: Toast["action"];
  duration?: number;
}

interface ToastContextValue {
  toast: (message: string, options?: ToastOptions) => void;
  success: (message: string, options?: ToastOptions) => void;
  error: (message: string, options?: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    // A missing provider should never silence feedback entirely.
    return {
      toast: (m) => console.info(m),
      success: (m) => console.info(m),
      error: (m) => console.error(m),
    };
  }
  return context;
}

const TONE_STYLES: Record<ToastTone, string> = {
  success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  error: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  info: "border-slate-700 bg-slate-900 text-slate-200",
};

const TONE_ICONS: Record<ToastTone, ReactNode> = {
  success: <CheckCircle2 className="h-4 w-4 shrink-0" />,
  error: <AlertCircle className="h-4 w-4 shrink-0" />,
  info: <Info className="h-4 w-4 shrink-0" />,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((message: string, options: ToastOptions = {}) => {
    const id = nextId.current++;
    setToasts((current) => [
      ...current.slice(-3),
      {
        id,
        message,
        tone: options.tone ?? "info",
        action: options.action,
        // An undoable action needs longer than a plain confirmation.
        duration: options.duration ?? (options.action ? 8000 : 4000),
      },
    ]);
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({
      toast: push,
      success: (message, options) => push(message, { ...options, tone: "success" }),
      error: (message, options) => push(message, { ...options, tone: "error" }),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-[100] flex flex-col items-center gap-2 p-4 sm:items-end sm:p-6"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), toast.duration);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  return (
    <div
      role="status"
      className={cn(
        "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur",
        TONE_STYLES[toast.tone],
      )}
    >
      {TONE_ICONS[toast.tone]}
      <span className="flex-1 leading-snug">{toast.message}</span>
      {toast.action && (
        <button
          type="button"
          onClick={() => {
            toast.action?.onClick();
            onDismiss(toast.id);
          }}
          className="shrink-0 rounded font-semibold underline underline-offset-2 hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-current"
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        className="shrink-0 rounded opacity-60 hover:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-current"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
