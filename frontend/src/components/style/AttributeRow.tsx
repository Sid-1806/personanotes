"use client";

import { Check, ChevronDown, Lock, RotateCcw, Unlock, X } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useOverrideAttribute, useResetAttribute } from "@/hooks/useStyle";
import { errorMessage } from "@/lib/api";
import { STYLE_ATTRIBUTES, confidenceLabel, describeAttribute } from "@/lib/styleAttributes";
import type { FeatureDetail } from "@/lib/types";
import { cn, formatAttributeValue, relativeTime } from "@/lib/utils";

/**
 * One learned style attribute, with the controls to correct it.
 *
 * The profile used to be a read-only report: you could watch the system form
 * opinions about your writing and could not change a single one, even though
 * the update endpoint existed. Pinning holds a value against future learning,
 * so "I always want tables" actually sticks.
 */
export function AttributeRow({ name, detail }: { name: string; detail: FeatureDetail }) {
  const meta = STYLE_ATTRIBUTES[name];
  const toast = useToast();
  const override = useOverrideAttribute();
  const reset = useResetAttribute();

  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState<string>(String(detail.value ?? ""));

  const pinned = detail.pinned ?? false;
  const confidence = detail.confidence ?? 0;
  const plain = describeAttribute(name, detail.value);
  const editable = meta && meta.control !== "readonly";

  const save = async () => {
    try {
      const parsed = meta?.control === "boolean" ? value === "true" : value;
      await override.mutateAsync({ feature: name, value: parsed, pinned: true });
      setEditing(false);
      toast.success(`${meta?.label ?? name} set — future notes will use it.`);
    } catch (saveError) {
      toast.error(errorMessage(saveError, "Couldn't save that."));
    }
  };

  const release = async () => {
    try {
      await reset.mutateAsync(name);
      toast.success(`${meta?.label ?? name} will be learned again from your notes.`);
    } catch (resetError) {
      toast.error(errorMessage(resetError, "Couldn't reset that."));
    }
  };

  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="text-sm font-medium text-slate-200">{meta?.label ?? name}</span>
          {pinned && (
            <Badge tone="info" className="ml-2">
              <Lock className="h-3 w-3" /> Pinned
            </Badge>
          )}
        </div>
        <span className="text-sm text-slate-100">{formatAttributeValue(detail.value)}</span>
      </div>

      {/* Plain English beats "bullet_frequency: 0.62". */}
      {plain && <p className="mt-1 text-sm text-slate-400">{plain}</p>}

      <div className="mt-2.5 flex items-center gap-3">
        <ProgressBar value={pinned ? 1 : confidence} className="flex-1" />
        <span
          className={cn(
            "shrink-0 text-xs",
            pinned ? "text-indigo-300" : confidence >= 0.5 ? "text-slate-400" : "text-amber-400",
          )}
        >
          {confidenceLabel(confidence, pinned)}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setExpanded((open) => !open)}
          aria-expanded={expanded}
          className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
        >
          Why this? <ChevronDown className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")} />
        </button>

        {editable && !editing && (
          <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
            Change
          </Button>
        )}
        {pinned && (
          <Button size="sm" variant="ghost" onClick={release} isLoading={reset.isPending}>
            <Unlock className="h-3 w-3" /> Learn it again
          </Button>
        )}
      </div>

      {expanded && (
        <div className="mt-2 rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-400">
          <p>{detail.reason}</p>
          <p className="mt-1.5 text-slate-500">
            {pinned
              ? "You set this by hand, so learning leaves it alone."
              : `Based on ${detail.observations ?? 0} observation${
                  (detail.observations ?? 0) === 1 ? "" : "s"
                } from your imported notes and edits.`}
            {detail.last_updated && ` · Updated ${relativeTime(detail.last_updated)}.`}
          </p>
          {meta?.help && <p className="mt-1.5 text-slate-500">{meta.help}</p>}
        </div>
      )}

      {editing && meta && (
        <div className="mt-3 flex flex-wrap items-end gap-2 rounded-lg border border-indigo-500/25 bg-indigo-500/5 p-3">
          <div className="min-w-0 flex-1">
            <label
              htmlFor={`attr-${name}`}
              className="mb-1 block text-xs font-medium text-slate-300"
            >
              {meta.label}
              {meta.unit ? ` (${meta.unit})` : ""}
            </label>
            {meta.control === "select" && meta.options ? (
              <Select id={`attr-${name}`} value={value} onChange={(e) => setValue(e.target.value)}>
                {meta.options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            ) : meta.control === "boolean" ? (
              <Select id={`attr-${name}`} value={value} onChange={(e) => setValue(e.target.value)}>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            ) : (
              <Input
                id={`attr-${name}`}
                type={meta.control === "number" ? "number" : "text"}
                step={meta.control === "number" ? "0.1" : undefined}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={meta.control === "list" ? "Comma-separated" : undefined}
              />
            )}
          </div>
          <div className="flex gap-1.5">
            <Button size="sm" onClick={save} isLoading={override.isPending}>
              <Check className="h-3.5 w-3.5" /> Pin it
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
          <p className="w-full text-xs text-slate-400">
            Pinning keeps this value fixed. Everything else keeps learning from your edits.
          </p>
        </div>
      )}
    </div>
  );
}

export function ResetProfileButton({ onReset, pending }: { onReset: () => void; pending: boolean }) {
  return (
    <Button variant="ghost" size="sm" onClick={onReset} isLoading={pending}>
      <RotateCcw className="h-3.5 w-3.5" /> Start the profile over
    </Button>
  );
}
