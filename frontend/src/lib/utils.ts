/** Tiny classnames helper (no dependency). Filters falsy values and joins. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/** Format a style-attribute value for display. */
export function formatAttributeValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(1);
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (typeof value === "object") return Object.keys(value as object).length ? "Custom" : "None";
  return String(value);
}

/** "3 minutes ago", "yesterday", "12 Mar" — short, human, and stable. */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.round((Date.now() - then) / 1000);

  if (seconds < 45) return "just now";
  if (seconds < 90) return "a minute ago";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** Rough reading time, at ~220 wpm. */
export function readingTime(words: number): string {
  const minutes = Math.max(1, Math.round(words / 220));
  return `${minutes} min read`;
}

export function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

/** Stable slug for heading anchors, matching the one the TOC builds. */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

/**
 * Promote single-line `$$...$$` equations to a display-math fence.
 *
 * `remark-math` only treats `$$` as *display* math when it opens a multi-line
 * fence; a one-line `$$x$$` is parsed as inline math text and renders squashed
 * into the surrounding paragraph. LLMs emit the one-line form constantly, so
 * normalising here is far more reliable than asking the model to stop.
 *
 * Lines inside fenced code blocks are left alone, and `$$` appearing mid-
 * sentence stays inline — only a line that is *entirely* one equation is
 * promoted.
 */
export function normalizeDisplayMath(markdown: string): string {
  if (!markdown || !markdown.includes("$$")) return markdown;

  const out: string[] = [];
  let inFence = false;

  for (const line of markdown.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      out.push(line);
      continue;
    }

    if (inFence) {
      out.push(line);
      continue;
    }

    const trimmed = line.trim();
    const match = /^\$\$(.+)\$\$$/.exec(trimmed);
    // The body must not itself contain `$$`, or this is several equations on
    // one line and splitting it would corrupt them.
    if (match && !match[1].includes("$$")) {
      out.push("$$", match[1].trim(), "$$");
      continue;
    }

    out.push(line);
  }

  return out.join("\n");
}

export interface Heading {
  depth: number;
  text: string;
  id: string;
}

/**
 * Extract headings for the table of contents.
 *
 * Fenced code blocks are skipped so a `# comment` inside a snippet never shows
 * up as a section.
 */
export function extractHeadings(markdown: string): Heading[] {
  const headings: Heading[] = [];
  const counts = new Map<string, number>();
  let inFence = false;

  for (const line of (markdown || "").split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;

    const match = /^(#{1,4})\s+(.*)$/.exec(line);
    if (!match) continue;

    const text = match[2].replace(/[*_`]/g, "").trim();
    if (!text) continue;

    const base = slugify(text) || "section";
    const seen = counts.get(base) ?? 0;
    counts.set(base, seen + 1);

    headings.push({
      depth: match[1].length,
      text,
      id: seen ? `${base}-${seen}` : base,
    });
  }
  return headings;
}

export const COURSE_COLORS = [
  "indigo",
  "emerald",
  "amber",
  "rose",
  "sky",
  "violet",
  "teal",
  "slate",
] as const;

export type CourseColor = (typeof COURSE_COLORS)[number];

/** Tailwind classes per course accent. Written out so JIT keeps them. */
export const COURSE_COLOR_CLASSES: Record<string, { dot: string; chip: string; ring: string }> = {
  indigo: { dot: "bg-indigo-400", chip: "bg-indigo-500/10 text-indigo-300 border-indigo-500/25", ring: "group-hover:border-indigo-500/50" },
  emerald: { dot: "bg-emerald-400", chip: "bg-emerald-500/10 text-emerald-300 border-emerald-500/25", ring: "group-hover:border-emerald-500/50" },
  amber: { dot: "bg-amber-400", chip: "bg-amber-500/10 text-amber-300 border-amber-500/25", ring: "group-hover:border-amber-500/50" },
  rose: { dot: "bg-rose-400", chip: "bg-rose-500/10 text-rose-300 border-rose-500/25", ring: "group-hover:border-rose-500/50" },
  sky: { dot: "bg-sky-400", chip: "bg-sky-500/10 text-sky-300 border-sky-500/25", ring: "group-hover:border-sky-500/50" },
  violet: { dot: "bg-violet-400", chip: "bg-violet-500/10 text-violet-300 border-violet-500/25", ring: "group-hover:border-violet-500/50" },
  teal: { dot: "bg-teal-400", chip: "bg-teal-500/10 text-teal-300 border-teal-500/25", ring: "group-hover:border-teal-500/50" },
  slate: { dot: "bg-slate-400", chip: "bg-slate-500/10 text-slate-300 border-slate-500/25", ring: "group-hover:border-slate-500/50" },
};

export function courseColor(color: string | null | undefined) {
  return COURSE_COLOR_CLASSES[color ?? "indigo"] ?? COURSE_COLOR_CLASSES.indigo;
}

export const NOTE_TYPE_LABELS: Record<string, string> = {
  full: "Full notes",
  summary: "Summary",
  key_concepts: "Key concepts",
  practice: "Practice questions",
  cheatsheet: "Cheat sheet",
  custom: "Custom",
  saved_answer: "Saved answer",
};

export function noteTypeLabel(type: string | null | undefined): string {
  return NOTE_TYPE_LABELS[type ?? "full"] ?? "Notes";
}

/** Read/write a draft so unsaved editor content survives a reload or re-auth. */
export const draftStore = {
  key: (noteId: number | string) => `personanotes:draft:${noteId}`,
  read(noteId: number | string): string | null {
    try {
      return sessionStorage.getItem(this.key(noteId));
    } catch {
      return null;
    }
  },
  write(noteId: number | string, value: string) {
    try {
      sessionStorage.setItem(this.key(noteId), value);
    } catch {
      /* storage can be unavailable; the editor still works in-memory */
    }
  },
  clear(noteId: number | string) {
    try {
      sessionStorage.removeItem(this.key(noteId));
    } catch {
      /* ignore */
    }
  },
};
