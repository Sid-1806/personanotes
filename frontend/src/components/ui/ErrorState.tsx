"use client";

import { AlertCircle, Clock, RefreshCw, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ApiError, errorKind, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * One error surface for every failure, told apart by kind.
 *
 * Everything used to read "Please try again" — a rate limit was
 * indistinguishable from a server fault, so the user had no idea whether
 * waiting would help.
 */
export function ErrorNotice({
  error,
  onRetry,
  className,
  compact = false,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}) {
  const kind = errorKind(error);
  const retryAfter = error instanceof ApiError ? error.retryAfter : null;
  const [remaining, setRemaining] = useState(retryAfter ?? 0);

  useEffect(() => {
    setRemaining(retryAfter ?? 0);
  }, [retryAfter]);

  useEffect(() => {
    if (kind !== "rate_limited" || remaining <= 0) return;
    const timer = setInterval(() => setRemaining((value) => Math.max(0, value - 1)), 1000);
    return () => clearInterval(timer);
  }, [kind, remaining]);

  const { icon, title, body, tone } = describe(kind, error, remaining);

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-lg border px-4 py-3 text-sm",
        tone === "warning"
          ? "border-amber-500/25 bg-amber-500/10 text-amber-200"
          : "border-rose-500/25 bg-rose-500/10 text-rose-200",
        className,
      )}
    >
      <span className="mt-0.5 shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        {!compact && <p className="font-medium">{title}</p>}
        <p className={cn(compact ? "" : "mt-0.5 opacity-90")}>{body}</p>
      </div>
      {onRetry && (kind !== "rate_limited" || remaining === 0) && (
        <Button size="sm" variant="ghost" onClick={onRetry} className="shrink-0">
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </Button>
      )}
    </div>
  );
}

function describe(kind: string, error: unknown, remaining: number) {
  switch (kind) {
    case "network":
      return {
        icon: <WifiOff className="h-4 w-4" />,
        title: "Can't reach PersonaNotes",
        body: "Check your connection — nothing you've typed has been lost.",
        tone: "warning" as const,
      };
    case "rate_limited":
      return {
        icon: <Clock className="h-4 w-4" />,
        title: "Slow down a moment",
        body:
          remaining > 0
            ? `You've hit the generation limit. Try again in ${remaining}s.`
            : "You can try again now.",
        tone: "warning" as const,
      };
    case "unavailable":
      return {
        icon: <AlertCircle className="h-4 w-4" />,
        title: "The AI service is unavailable",
        body: errorMessage(error, "This is usually brief — retry in a moment."),
        tone: "warning" as const,
      };
    case "not_found":
      return {
        icon: <AlertCircle className="h-4 w-4" />,
        title: "Not found",
        body: errorMessage(error, "This may have been deleted, or it isn't yours."),
        tone: "error" as const,
      };
    case "validation":
    case "conflict":
      return {
        icon: <AlertCircle className="h-4 w-4" />,
        title: "That didn't work",
        body: errorMessage(error),
        tone: "warning" as const,
      };
    default:
      return {
        icon: <AlertCircle className="h-4 w-4" />,
        title: "Something went wrong",
        body: errorMessage(error, "Please try again."),
        tone: "error" as const,
      };
  }
}

/** Full-page failure, for when a route's primary query can't load. */
export function ErrorPage({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
      <AlertCircle className="mb-4 h-10 w-10 text-rose-400" />
      <h2 className="text-lg font-semibold text-slate-100">This page couldn&apos;t load</h2>
      <p className="mt-2 max-w-md text-sm text-slate-400">{errorMessage(error)}</p>
      {onRetry && (
        <Button className="mt-6" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" /> Try again
        </Button>
      )}
    </div>
  );
}
