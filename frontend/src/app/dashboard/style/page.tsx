"use client";

import { BrainCircuit, Eye, History, Sparkles, Trash2, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Markdown } from "@/components/notes/Markdown";
import { UploadDropzone } from "@/components/lectures/UploadDropzone";
import { AttributeRow, ResetProfileButton } from "@/components/style/AttributeRow";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorPage } from "@/components/ui/ErrorState";
import { Modal } from "@/components/ui/Modal";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/Toast";
import {
  useDeleteHistorical,
  useHistoricalSources,
  useImportHistorical,
  useResetProfile,
  useRestoreStyleVersion,
  useStyleDashboard,
  useStyleProgress,
  useStylePreview,
} from "@/hooks/useStyle";
import { errorMessage } from "@/lib/api";
import { CATEGORY_BLURB, CATEGORY_ORDER, STYLE_ATTRIBUTES } from "@/lib/styleAttributes";
import type { StyleProfileDetail } from "@/lib/types";
import { relativeTime } from "@/lib/utils";

function averageConfidence(profile: StyleProfileDetail): number {
  const values = Object.values(profile).map((d) => d.confidence);
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/**
 * The style profile: what's been learned, why, and the controls to correct it.
 *
 * Historical notes live here under Sources rather than in the top-level nav:
 * they are style training data, not a second content library.
 */
function StyleInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const toast = useToast();

  const [tab, setTab] = useState(searchParams.get("tab") ?? "profile");
  const [confirmReset, setConfirmReset] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const { data, isLoading, isError, error, refetch } = useStyleDashboard();
  const resetProfile = useResetProfile();

  if (isError) return <ErrorPage error={error} onRetry={() => refetch()} />;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  const profile = data?.current_profile ?? {};
  const hasProfile = Object.keys(profile).length > 0;
  const average = averageConfidence(profile);

  const changeTab = (next: string) => {
    setTab(next);
    router.replace(`/dashboard/style?tab=${next}`);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-100">
          <BrainCircuit className="h-6 w-6 text-indigo-400" /> Your style
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          What PersonaNotes has learned about how you take notes — and what you can change.
        </p>
      </div>

      <Tabs
        items={[
          { id: "profile", label: "Profile" },
          { id: "sources", label: "Sources" },
          { id: "progress", label: "Progress" },
        ]}
        active={tab}
        onChange={changeTab}
      />

      {tab === "profile" &&
        (!hasProfile ? (
          <EmptyState
            icon={<BrainCircuit className="h-14 w-14" />}
            title="No style learned yet"
            description="Import a few of your past notes, or edit some generated ones. PersonaNotes picks up how you write and matches it."
            action={
              <div className="flex flex-wrap justify-center gap-3">
                <Button onClick={() => changeTab("sources")}>Add past notes</Button>
                <Link href="/dashboard/generate">
                  <Button variant="secondary">Generate notes</Button>
                </Link>
              </div>
            }
          />
        ) : (
          <div className="space-y-6">
            <Card>
              <CardBody className="flex flex-wrap items-start gap-6">
                <div className="min-w-[180px]">
                  <p className="text-sm text-slate-400">Overall confidence</p>
                  <p className="mt-1 text-4xl font-bold text-slate-100">
                    {Math.round(average * 100)}%
                  </p>
                  <div className="mt-3">
                    <ProgressBar value={average} />
                  </div>
                  <p className="mt-2 text-xs text-slate-400">
                    Across {Object.keys(profile).length} attributes
                  </p>
                </div>

                <div className="flex-1 space-y-3">
                  <SourceBreakdown sources={data?.sources ?? {}} />
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="secondary" onClick={() => setShowPreview(true)}>
                      <Eye className="h-3.5 w-3.5" /> See a sample in my style
                    </Button>
                    <ResetProfileButton
                      onReset={() => setConfirmReset(true)}
                      pending={resetProfile.isPending}
                    />
                  </div>
                </div>
              </CardBody>
            </Card>

            <div className="grid gap-6 lg:grid-cols-2">
              {CATEGORY_ORDER.map((category) => {
                const rows = Object.entries(profile).filter(
                  ([name]) => STYLE_ATTRIBUTES[name]?.category === category,
                );
                if (!rows.length) return null;
                return (
                  <Card key={category}>
                    <CardHeader>
                      <h2 className="text-sm font-semibold text-slate-200">{category}</h2>
                      <p className="mt-0.5 text-xs text-slate-400">{CATEGORY_BLURB[category]}</p>
                    </CardHeader>
                    <CardBody className="divide-y divide-slate-800 py-2">
                      {rows.map(([name, detail]) => (
                        <AttributeRow key={name} name={name} detail={detail} />
                      ))}
                    </CardBody>
                  </Card>
                );
              })}
            </div>

            <VersionTimeline versions={data?.versions ?? []} />
          </div>
        ))}

      {tab === "sources" && <SourcesTab />}
      {tab === "progress" && <ProgressTab />}

      <StylePreviewModal open={showPreview} onClose={() => setShowPreview(false)} />

      <Modal
        open={confirmReset}
        onClose={() => setConfirmReset(false)}
        title="Start your style profile over?"
        description="Everything learned so far is cleared. The current profile is kept as a version you can restore."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmReset(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              isLoading={resetProfile.isPending}
              onClick={async () => {
                try {
                  await resetProfile.mutateAsync();
                  toast.success("Style profile reset.");
                  setConfirmReset(false);
                } catch (resetError) {
                  toast.error(errorMessage(resetError, "Couldn't reset the profile."));
                }
              }}
            >
              Reset profile
            </Button>
          </>
        }
      />
    </div>
  );
}

function SourceBreakdown({ sources }: { sources: Record<string, number> }) {
  const labels: Record<string, string> = {
    historical_notes: "Notes you imported",
    edited_notes: "Your edits",
    generated_feedback: "Feedback",
  };
  const entries = Object.entries(sources ?? {}).filter(([, value]) => value > 0);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <p className="mb-3 text-xs text-slate-400">What shaped your style</p>
      {entries.length === 0 ? (
        <p className="text-xs text-slate-400">
          Nothing yet — import past notes or edit a generated one.
        </p>
      ) : (
        <div className="space-y-2">
          {entries.map(([key, weight]) => (
            <div key={key} className="flex items-center gap-3">
              <span className="w-32 shrink-0 text-xs text-slate-400">{labels[key] ?? key}</span>
              <ProgressBar value={weight} />
              <span className="w-10 shrink-0 text-right text-xs text-slate-400">
                {Math.round(weight * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function VersionTimeline({
  versions,
}: {
  versions: { version: number; created_at: string }[];
}) {
  const restore = useRestoreStyleVersion();
  const toast = useToast();

  if (!versions.length) return null;

  return (
    <Card>
      <CardHeader>
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <History className="h-4 w-4 text-indigo-400" /> Profile history
        </h2>
        <p className="mt-0.5 text-xs text-slate-400">
          Every change is snapshotted, so nothing here is one-way.
        </p>
      </CardHeader>
      <CardBody>
        <ol className="space-y-2">
          {versions
            .slice()
            .reverse()
            .slice(0, 8)
            .map((version) => (
              <li key={version.version} className="flex flex-wrap items-center gap-3 text-sm">
                <Badge tone="info">v{version.version}</Badge>
                <span className="flex-1 text-slate-400">{relativeTime(version.created_at)}</span>
                <Button
                  size="sm"
                  variant="ghost"
                  isLoading={restore.isPending && restore.variables === version.version}
                  onClick={async () => {
                    try {
                      await restore.mutateAsync(version.version);
                      toast.success(`Restored version ${version.version}.`);
                    } catch (restoreError) {
                      toast.error(errorMessage(restoreError, "Couldn't restore that version."));
                    }
                  }}
                >
                  Restore
                </Button>
              </li>
            ))}
        </ol>
      </CardBody>
    </Card>
  );
}

function SourcesTab() {
  const { data: sources, isLoading } = useHistoricalSources();
  const importHistorical = useImportHistorical();
  const removeSource = useDeleteHistorical();
  const toast = useToast();

  const upload = async (files: File[]) => {
    try {
      const result = await importHistorical.mutateAsync(files);
      toast.success(
        `Learned from ${result.imported_count} note${result.imported_count === 1 ? "" : "s"}.`,
      );
      if (result.skipped?.length) {
        toast.toast(`${result.skipped.length} file(s) had no readable text.`, { tone: "info" });
      }
    } catch (uploadError) {
      toast.error(errorMessage(uploadError, "Those files couldn't be analysed."));
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-semibold text-slate-100">Notes that taught your style</h2>
        <p className="mt-1 text-sm text-slate-400">
          Upload notes you wrote yourself. Removing one recomputes your profile without it — so a
          bad import isn&apos;t permanent.
        </p>
      </div>

      <UploadDropzone
        onFiles={upload}
        uploading={importHistorical.isPending}
        error={importHistorical.isError ? importHistorical.error : undefined}
        hint="Markdown, PDF or text notes you wrote."
        compact={(sources?.length ?? 0) > 0}
      />

      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : !sources?.length ? (
        <p className="py-4 text-sm text-slate-400">
          No sources yet. One to three of your own notes is enough to get started.
        </p>
      ) : (
        <ul className="space-y-2">
          {sources.map((source) => (
            <li
              key={source.id}
              className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-slate-200">{source.title}</p>
                <p className="text-xs text-slate-400">
                  Added {relativeTime(source.created_at)} · {source.analysis_status}
                </p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                isLoading={removeSource.isPending && removeSource.variables === source.id}
                onClick={async () => {
                  try {
                    await removeSource.mutateAsync(source.id);
                    toast.success("Source removed — your profile was recomputed without it.");
                  } catch (deleteError) {
                    toast.error(errorMessage(deleteError, "Couldn't remove that source."));
                  }
                }}
              >
                <Trash2 className="h-3.5 w-3.5" /> Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ProgressTab() {
  const { data, isLoading } = useStyleProgress();

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  if (!data?.measured) {
    return (
      <EmptyState
        icon={<TrendingUp className="h-12 w-12" />}
        title="Nothing measured yet"
        description="Edit a generated note and save it. PersonaNotes compares what it wrote with what you wanted, and tracks whether the gap is closing."
        action={
          <Link href="/dashboard/notes">
            <Button>Go to your notes</Button>
          </Link>
        }
      />
    );
  }

  const max = Math.max(...data.points.map((p) => p.score), 100);

  return (
    <div className="space-y-5">
      <Card>
        <CardBody className="flex flex-wrap items-center gap-8">
          <div>
            <p className="text-sm text-slate-400">Latest style match</p>
            <p className="mt-1 text-4xl font-bold text-slate-100">{data.current_score}%</p>
          </div>
          <div>
            <p className="text-sm text-slate-400">Since you started</p>
            <p
              className={`mt-1 text-4xl font-bold ${
                (data.trend ?? 0) >= 0 ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {(data.trend ?? 0) >= 0 ? "+" : ""}
              {data.trend}
            </p>
          </div>
          <div className="min-w-[200px] flex-1">
            <p className="mb-2 text-xs text-slate-400">
              How closely each generation matched what you kept
            </p>
            <div className="flex h-20 items-end gap-1">
              {data.points.slice(-24).map((point, index) => (
                <div
                  key={index}
                  className="flex-1 rounded-t bg-indigo-500/60"
                  style={{ height: `${Math.max(4, (point.score / max) * 100)}%` }}
                  title={`${Math.round(point.score)}%`}
                />
              ))}
            </div>
          </div>
        </CardBody>
      </Card>

      {data.insights.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-200">What&apos;s changed</h2>
          </CardHeader>
          <CardBody>
            <ul className="space-y-2">
              {data.insights.map((insight, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-slate-300">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                  {insight}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function StylePreviewModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data, isLoading } = useStylePreview(open);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="A sample in your style"
      description="The same short topic, written the way PersonaNotes thinks you'd write it."
      size="lg"
    >
      {isLoading ? <Skeleton className="h-48 w-full" /> : <Markdown>{data?.markdown ?? ""}</Markdown>}
    </Modal>
  );
}

export default function StylePage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <StyleInner />
    </Suspense>
  );
}
