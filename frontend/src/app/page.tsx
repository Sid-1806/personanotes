import { ArrowRight, BookOpen, GitCompare, Quote, Search, Sparkles } from "lucide-react";
import Link from "next/link";

/**
 * Landing page.
 *
 * The old one was three buttons and a single sentence — it never said what the
 * product does, and "Go to Dashboard" bounced signed-out visitors to a login
 * form. The one thing to communicate is the thing nothing else does: notes that
 * come out looking like the ones you write yourself.
 */
export const metadata = {
  title: "PersonaNotes — lecture notes in your own handwriting",
  description:
    "Upload your lectures, teach it how you write, and get notes that read like you wrote them — grounded in your own material.",
};

const GENERIC_SAMPLE = `Backpropagation is an algorithm used for training neural
networks. It works by computing the gradient of the loss
function with respect to each weight in the network. The
algorithm proceeds in two phases: a forward pass, in which
inputs are propagated through the network to produce an
output, and a backward pass, in which errors are propagated
back through the network to update the weights.`;

const PERSONAL_SAMPLE = `## Backpropagation

**Core idea:** chain rule, applied backwards through the net.

- **Forward pass** → compute activations, cache them
- **Backward pass** → propagate ∂L/∂z layer by layer
- **Update** → w ← w − η·∂L/∂w

| Phase | Computes | Needs |
|---|---|---|
| Forward | activations | inputs |
| Backward | gradients | cached activations |

> Why cache? Recomputing activations in the backward pass
> costs another full forward pass.`;

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="h-5 w-5 text-indigo-400" /> PersonaNotes
        </span>
        <nav className="flex items-center gap-2 text-sm">
          <Link
            href="/login"
            className="rounded-lg px-4 py-2 text-slate-300 hover:bg-slate-800 hover:text-slate-100"
          >
            Log in
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-indigo-500 px-4 py-2 font-medium text-white hover:bg-indigo-600"
          >
            Get started
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-16 pt-10 sm:pt-20">
        <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300">
          <Quote className="h-3 w-3" /> Grounded in your lectures. Written in your style.
        </p>
        <h1 className="max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
          Lecture notes that look like{" "}
          <span className="text-indigo-400">you wrote them</span>.
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-400">
          Generic AI summaries all read the same. PersonaNotes learns how{" "}
          <em className="text-slate-300">you</em> take notes — your headings, your bullets, your
          tone, how much you lean on examples — then writes new notes that match, using only your
          own uploaded lectures as source material.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-5 py-3 font-medium text-white hover:bg-indigo-600"
          >
            Start with your notes <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-5 py-3 font-medium text-slate-200 hover:bg-slate-800"
          >
            I already have an account
          </Link>
        </div>
      </section>

      {/* The actual claim, shown rather than asserted. */}
      <section className="mx-auto max-w-6xl px-6 pb-20">
        <h2 className="mb-6 text-sm font-semibold uppercase tracking-wider text-slate-500">
          The same lecture, two ways
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <article className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              A generic AI summary
            </p>
            <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-slate-400">
              {GENERIC_SAMPLE}
            </pre>
          </article>
          <article className="rounded-xl border border-indigo-500/30 bg-indigo-500/[0.04] p-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-indigo-400">
              PersonaNotes, after learning one of your past notes
            </p>
            <pre className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-slate-300">
              {PERSONAL_SAMPLE}
            </pre>
          </article>
        </div>
      </section>

      <section className="border-y border-slate-800 bg-slate-900/30">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-16 sm:grid-cols-2 lg:grid-cols-4">
          <Feature
            icon={<Sparkles className="h-5 w-5" />}
            title="It learns from your edits"
            body="Every time you rewrite a generated note, PersonaNotes notices what changed and adjusts. The notes need less editing each week."
          />
          <Feature
            icon={<BookOpen className="h-5 w-5" />}
            title="Grounded, with receipts"
            body="Notes are built from your own lectures, and every claim links back to the passage it came from — so you can check it."
          />
          <Feature
            icon={<Search className="h-5 w-5" />}
            title="Ask across a course"
            body="Semantic search and a study assistant that answers from your material, with citations, not from the open internet."
          />
          <Feature
            icon={<GitCompare className="h-5 w-5" />}
            title="Nothing gets lost"
            body="Your edits are saved as versions you can compare and roll back. Export everything as markdown whenever you want."
          />
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-6 py-20 text-center">
        <h2 className="text-2xl font-bold sm:text-3xl">Start with three of your old notes.</h2>
        <p className="mt-3 text-slate-400">
          That&apos;s all it takes to learn your style. Upload a lecture and the first set of notes
          already sounds like you.
        </p>
        <Link
          href="/register"
          className="mt-7 inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-6 py-3 font-medium text-white hover:bg-indigo-600"
        >
          Create your account <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      <footer className="border-t border-slate-800 px-6 py-8 text-center text-sm text-slate-500">
        PersonaNotes — personalized, grounded lecture notes.
      </footer>
    </main>
  );
}

function Feature({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div>
      <div className="mb-3 inline-flex rounded-lg bg-indigo-500/10 p-2.5 text-indigo-400">
        {icon}
      </div>
      <h3 className="mb-1.5 font-semibold text-slate-100">{title}</h3>
      <p className="text-sm leading-relaxed text-slate-400">{body}</p>
    </div>
  );
}
