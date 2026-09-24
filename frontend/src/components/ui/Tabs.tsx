"use client";

import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

/** Accessible tab strip. Scrolls rather than wrapping on narrow screens. */
export function Tabs({
  items,
  active,
  onChange,
  className,
}: {
  items: TabItem[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn(
        "-mx-4 flex gap-1 overflow-x-auto border-b border-slate-800 px-4 sm:mx-0 sm:px-0",
        className,
      )}
    >
      {items.map((item) => {
        const isActive = item.id === active;
        return (
          <button
            key={item.id}
            role="tab"
            type="button"
            aria-selected={isActive}
            onClick={() => onChange(item.id)}
            className={cn(
              "-mb-px shrink-0 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50",
              isActive
                ? "border-indigo-400 text-indigo-300"
                : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-200",
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span className="ml-2 rounded-full bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
