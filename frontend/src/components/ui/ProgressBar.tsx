import { cn } from "@/lib/utils";

/** A thin confidence/progress bar. `value` is 0..1. */
export function ProgressBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  const color = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-indigo-500" : "bg-amber-500";
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-slate-800", className)}>
      <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
    </div>
  );
}
