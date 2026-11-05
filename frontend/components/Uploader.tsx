"use client";

import { useEffect, useMemo, useRef } from "react";
import { ACCEPT } from "@/lib/files";
import type { Texts } from "@/lib/i18n";
import type { DocType } from "@/lib/types";

interface Props {
  t: Texts;
  files: File[];
  docType: DocType | "auto";
  busy: boolean;
  onAdd: (files: File[]) => void;
  onRemove: (index: number) => void;
  onDocType: (d: DocType | "auto") => void;
  onSubmit: () => void;
}

const DOC_TYPES: (DocType | "auto")[] = ["auto", "rental", "phone_plan", "part_time"];

export default function Uploader({ t, files, docType, busy, onAdd, onRemove, onDocType, onSubmit }: Props) {
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);

  // object URLs for the thumbnails; revoked when the files change so memory is freed
  const previews = useMemo(
    () => files.map((f) => (f.type.startsWith("image/") ? URL.createObjectURL(f) : null)),
    [files],
  );
  useEffect(() => () => previews.forEach((u) => u && URL.revokeObjectURL(u)), [previews]);

  function picked(e: React.ChangeEvent<HTMLInputElement>) {
    const list = Array.from(e.target.files ?? []);
    e.target.value = ""; // lets the same photo be chosen again
    if (list.length) onAdd(list);
  }

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">{t.addPhoto}</h2>

      <div className="grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => camera.current?.click()}
          disabled={busy}
          className="rounded-xl bg-brand px-4 text-base font-semibold text-brand-ink disabled:opacity-50"
        >
          📷 {t.takePhoto}
        </button>
        <button
          type="button"
          onClick={() => gallery.current?.click()}
          disabled={busy}
          className="rounded-xl border border-line bg-card px-4 text-base font-semibold disabled:opacity-50"
        >
          🖼️ {t.choosePhoto}
        </button>
      </div>
      {/* capture opens the rear camera on phones; on a computer it behaves like a file picker */}
      <input ref={camera} type="file" accept="image/*" capture="environment" hidden onChange={picked} />
      <input ref={gallery} type="file" accept={ACCEPT} multiple hidden onChange={picked} />

      <p className="text-sm text-muted">{t.tipText}</p>

      {files.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm font-medium" aria-live="polite">
            {t.pagesAdded(files.length)}
          </p>
          <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="relative overflow-hidden rounded-lg border border-line bg-card">
                {previews[i] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={previews[i]!} alt={`${i + 1}`} className="aspect-[3/4] w-full object-cover" />
                ) : (
                  <div className="flex aspect-[3/4] items-center justify-center text-sm text-muted">PDF</div>
                )}
                <span className="absolute left-1 top-1 rounded bg-black/60 px-1.5 text-xs text-white">{i + 1}</span>
                <button
                  type="button"
                  onClick={() => onRemove(i)}
                  disabled={busy}
                  aria-label={`${t.remove} ${i + 1}`}
                  className="absolute right-1 top-1 flex h-8 min-h-0 w-8 items-center justify-center rounded-full bg-black/60 text-white"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <label className="block space-y-1">
        <span className="text-sm font-medium">{t.docTypeLabel}</span>
        <select
          value={docType}
          onChange={(e) => onDocType(e.target.value as DocType | "auto")}
          disabled={busy}
          className="w-full rounded-xl border border-line bg-card px-3 py-3 text-base"
        >
          {DOC_TYPES.map((d) => (
            <option key={d} value={d}>
              {t.docTypes[d]}
            </option>
          ))}
        </select>
      </label>

      <button
        type="button"
        onClick={onSubmit}
        disabled={busy || files.length === 0}
        className="w-full rounded-xl bg-brand px-4 text-base font-semibold text-brand-ink disabled:opacity-40"
      >
        {busy ? t.uploading : t.analyze}
      </button>
    </section>
  );
}
