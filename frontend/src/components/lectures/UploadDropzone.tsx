"use client";

import { Camera, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

import { ErrorNotice } from "@/components/ui/ErrorState";
import { cn } from "@/lib/utils";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.txt,.md";

/**
 * Multi-file upload target.
 *
 * Accepts a whole week at once, and on a phone offers the camera directly —
 * photographing a handout or a whiteboard is a genuinely good mobile flow, and
 * the OCR path on the server already handles images.
 */
export function UploadDropzone({
  onFiles,
  uploading = false,
  error,
  compact = false,
  hint,
}: {
  onFiles: (files: File[]) => void;
  uploading?: boolean;
  error?: unknown;
  compact?: boolean;
  hint?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handle = (list: FileList | null) => {
    const files = Array.from(list ?? []);
    if (files.length) onFiles(files);
    if (inputRef.current) inputRef.current.value = "";
    if (cameraRef.current) cameraRef.current.value = "";
  };

  return (
    <div>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          handle(event.dataTransfer.files);
        }}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed text-center transition-colors",
          compact ? "px-4 py-6" : "px-6 py-10",
          dragging
            ? "border-indigo-500 bg-indigo-500/10"
            : "border-slate-700 bg-slate-900/30 hover:border-indigo-500/50 hover:bg-slate-800/40",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(event) => handle(event.target.files)}
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(event) => handle(event.target.files)}
        />

        <UploadCloud className={cn("mb-3 text-indigo-400", compact ? "h-6 w-6" : "h-8 w-8")} />
        <p className="text-sm font-medium text-slate-200">
          {uploading ? "Uploading…" : "Drop files here, or choose below"}
        </p>
        <p className="mt-1 max-w-sm text-xs text-slate-400">
          {hint ?? "PDF, image, TXT or MD. Scans and photos are read with OCR."}
        </p>

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            Choose files
          </button>
          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            disabled={uploading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50 sm:hidden"
          >
            <Camera className="h-4 w-4" /> Take a photo
          </button>
        </div>
      </div>

      {error ? <ErrorNotice error={error} className="mt-3" /> : null}
    </div>
  );
}
