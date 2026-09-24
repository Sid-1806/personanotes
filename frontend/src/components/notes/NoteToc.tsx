"use client";

import { List, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Heading, cn, extractHeadings } from "@/lib/utils";

/**
 * Table of contents with scroll-spy.
 *
 * A 3,000-word note without one is a single unbroken scroll; this is the
 * difference between reading a note and searching it by eye.
 */
export function NoteToc({
  markdown,
  className,
  onNavigate,
}: {
  markdown: string;
  className?: string;
  onNavigate?: () => void;
}) {
  const headings = useMemo(() => extractHeadings(markdown), [markdown]);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    if (!headings.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      // Bias the band toward the top of the viewport so the highlighted item
      // is the section you're reading, not one just scrolled past.
      { rootMargin: "-80px 0px -65% 0px", threshold: 0 },
    );

    const timer = window.setTimeout(() => {
      headings.forEach(({ id }) => {
        const element = document.getElementById(id);
        if (element) observer.observe(element);
      });
    }, 120);

    return () => {
      window.clearTimeout(timer);
      observer.disconnect();
    };
  }, [headings, markdown]);

  if (headings.length < 2) return null;

  const minDepth = Math.min(...headings.map((h) => h.depth));

  return (
    <nav aria-label="Table of contents" className={className}>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        On this page
      </p>
      <ul className="space-y-0.5 border-l border-slate-800">
        {headings.map((heading) => (
          <TocLink
            key={heading.id}
            heading={heading}
            minDepth={minDepth}
            active={heading.id === activeId}
            onNavigate={onNavigate}
          />
        ))}
      </ul>
    </nav>
  );
}

function TocLink({
  heading,
  minDepth,
  active,
  onNavigate,
}: {
  heading: Heading;
  minDepth: number;
  active: boolean;
  onNavigate?: () => void;
}) {
  const indent = Math.min(heading.depth - minDepth, 2);
  return (
    <li>
      <a
        href={`#${heading.id}`}
        onClick={(event) => {
          event.preventDefault();
          const element = document.getElementById(heading.id);
          element?.scrollIntoView({ behavior: "smooth", block: "start" });
          // Keep the URL shareable without triggering a jump.
          window.history.replaceState(null, "", `#${heading.id}`);
          onNavigate?.();
        }}
        className={cn(
          "-ml-px block border-l-2 py-1 text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50",
          active
            ? "border-indigo-400 font-medium text-indigo-300"
            : "border-transparent text-slate-400 hover:border-slate-600 hover:text-slate-200",
          indent === 0 && "pl-3",
          indent === 1 && "pl-6",
          indent === 2 && "pl-9",
        )}
      >
        {heading.text}
      </a>
    </li>
  );
}

/** Floating TOC trigger for phones, where there is no room for a sidebar. */
export function MobileToc({ markdown }: { markdown: string }) {
  const [open, setOpen] = useState(false);
  const headings = useMemo(() => extractHeadings(markdown), [markdown]);

  if (headings.length < 2) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open table of contents"
        className="fixed bottom-20 right-4 z-40 flex h-11 w-11 items-center justify-center rounded-full border border-slate-700 bg-slate-900/95 text-slate-200 shadow-lg backdrop-blur focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 lg:hidden"
      >
        <List className="h-5 w-5" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[80] lg:hidden">
          <div
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div className="absolute inset-x-0 bottom-0 max-h-[70vh] overflow-y-auto rounded-t-2xl border-t border-slate-800 bg-slate-900 p-5">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-200">Contents</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close table of contents"
                className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <NoteToc markdown={markdown} onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
