"use client";

import { Check, Copy } from "lucide-react";
import { ReactNode, isValidElement, useState } from "react";
import ReactMarkdown, { Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { MermaidDiagram } from "@/components/notes/MermaidDiagram";
import { cn, normalizeDisplayMath, slugify } from "@/lib/utils";

import "katex/dist/katex.min.css";
import "highlight.js/styles/github-dark.css";

/**
 * Note renderer.
 *
 * GFM, maths and syntax highlighting are all load-bearing rather than polish:
 * the style profile tracks table and code-block frequency and the generation
 * prompt asks for both, so without `remark-gfm` a table the model was told to
 * produce rendered as literal pipes. `remark-math` matters for any STEM course.
 */

/** Heading ids, numbered on collision, matching `extractHeadings` for the TOC. */
function useHeadingIds() {
  const counts = new Map<string, number>();
  return (children: ReactNode): string => {
    const text = extractText(children);
    const base = slugify(text) || "section";
    const seen = counts.get(base) ?? 0;
    counts.set(base, seen + 1);
    return seen ? `${base}-${seen}` : base;
  };
}

function extractText(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (isValidElement(node)) {
    return extractText((node.props as { children?: ReactNode }).children);
  }
  return "";
}

function CodeBlock({ children, className }: { children: ReactNode; className?: string }) {
  const [copied, setCopied] = useState(false);
  const text = extractText(children);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard can be blocked; the code is still selectable */
    }
  };

  const language = /language-(\w+)/.exec(className ?? "")?.[1];

  return (
    <div className="group relative mb-4">
      <div className="flex items-center justify-between rounded-t-lg border border-b-0 border-slate-800 bg-slate-900/80 px-3 py-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {language ?? "code"}
        </span>
        <button
          type="button"
          onClick={copy}
          aria-label={copied ? "Code copied" : "Copy code"}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-slate-400 transition-colors hover:text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto rounded-b-lg border border-slate-800 bg-slate-950 p-4 text-sm">
        {children}
      </pre>
    </div>
  );
}

export function Markdown({
  children,
  className,
  compact = false,
}: {
  children: string;
  className?: string;
  /** Tighter spacing for chat answers and previews. */
  compact?: boolean;
}) {
  const headingId = useHeadingIds();

  const components: Components = {
    h1: ({ node, children, ...props }) => (
      <h1
        id={headingId(children)}
        className="mb-4 mt-8 scroll-mt-24 text-2xl font-bold tracking-tight text-slate-50 first:mt-0 sm:text-3xl"
        {...props}
      >
        {children}
      </h1>
    ),
    h2: ({ node, children, ...props }) => (
      <h2
        id={headingId(children)}
        className="mb-3 mt-8 scroll-mt-24 border-b border-slate-800 pb-2 text-xl font-semibold tracking-tight text-slate-100 first:mt-0 sm:text-2xl"
        {...props}
      >
        {children}
      </h2>
    ),
    h3: ({ node, children, ...props }) => (
      <h3
        id={headingId(children)}
        className="mb-2 mt-6 scroll-mt-24 text-lg font-semibold text-slate-100"
        {...props}
      >
        {children}
      </h3>
    ),
    h4: ({ node, children, ...props }) => (
      <h4
        id={headingId(children)}
        className="mb-2 mt-5 scroll-mt-24 text-base font-semibold text-slate-200"
        {...props}
      >
        {children}
      </h4>
    ),
    p: ({ node, ...props }) => (
      <p className={cn("text-slate-300", compact ? "mb-2" : "mb-4")} {...props} />
    ),
    ul: ({ node, ...props }) => (
      <ul
        className={cn("ml-5 list-disc space-y-1.5 text-slate-300", compact ? "mb-2" : "mb-4")}
        {...props}
      />
    ),
    ol: ({ node, ...props }) => (
      <ol
        className={cn("ml-5 list-decimal space-y-1.5 text-slate-300", compact ? "mb-2" : "mb-4")}
        {...props}
      />
    ),
    li: ({ node, ...props }) => <li className="leading-relaxed marker:text-slate-600" {...props} />,
    strong: ({ node, ...props }) => (
      <strong className="font-semibold text-slate-100" {...props} />
    ),
    em: ({ node, ...props }) => <em className="italic" {...props} />,
    hr: ({ node, ...props }) => <hr className="my-8 border-slate-800" {...props} />,
    code: ({ node, className, children, ...props }) => {
      if (typeof className === "string" && className.includes("language-mermaid")) {
        return <MermaidDiagram chart={extractText(children).replace(/\n$/, "")} />;
      }
      // An inline code span has no language class from the highlighter.
      if (!className) {
        return (
          <code
            className="rounded bg-slate-800/80 px-1.5 py-0.5 text-[0.9em] text-indigo-300"
            {...props}
          >
            {children}
          </code>
        );
      }
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    pre: ({ node, children, ...props }) => {
      const child = Array.isArray(children) ? children[0] : children;
      const childClass = isValidElement(child)
        ? (child.props as { className?: string }).className
        : undefined;
      // Mermaid blocks become diagrams in the `code` handler, so skip the <pre>.
      if (typeof childClass === "string" && childClass.includes("language-mermaid")) {
        return <>{children}</>;
      }
      return <CodeBlock className={childClass}>{children}</CodeBlock>;
    },
    blockquote: ({ node, ...props }) => (
      <blockquote
        className="mb-4 border-l-2 border-indigo-500/40 bg-slate-900/40 py-2 pl-4 pr-3 italic text-slate-400"
        {...props}
      />
    ),
    a: ({ node, ...props }) => (
      <a
        className="text-indigo-400 underline decoration-indigo-500/40 underline-offset-2 hover:text-indigo-300"
        target="_blank"
        rel="noreferrer noopener"
        {...props}
      />
    ),
    // Tables scroll rather than overflowing the column on a phone.
    table: ({ node, ...props }) => (
      <div className="mb-4 -mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <table className="w-full border-collapse text-sm" {...props} />
      </div>
    ),
    thead: ({ node, ...props }) => <thead className="bg-slate-900/60" {...props} />,
    th: ({ node, ...props }) => (
      <th
        className="border border-slate-800 px-3 py-2 text-left font-semibold text-slate-200"
        {...props}
      />
    ),
    td: ({ node, ...props }) => (
      <td className="border border-slate-800 px-3 py-2 align-top text-slate-300" {...props} />
    ),
    input: ({ node, ...props }) => (
      // GFM task lists render as checkboxes; they're a view of the text, not a control.
      <input
        className="mr-1.5 h-3.5 w-3.5 rounded border-slate-600 align-middle accent-indigo-500"
        disabled
        {...props}
      />
    ),
    img: ({ node, ...props }) => (
      // eslint-disable-next-line @next/next/no-img-element
      <img className="mb-4 max-w-full rounded-lg border border-slate-800" alt="" {...props} />
    ),
  };

  return (
    <div className={cn("note-prose", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex, [rehypeHighlight, { ignoreMissing: true, detect: true }]]}
        components={components}
      >
        {normalizeDisplayMath(children)}
      </ReactMarkdown>
    </div>
  );
}
