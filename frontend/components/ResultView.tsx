"use client";

import { sortFlags } from "@/lib/flags";
import type { Texts } from "@/lib/i18n";
import type { Explanation, Severity } from "@/lib/types";

const STYLE: Record<Severity, string> = {
  high: "border-[var(--high)] bg-[var(--high-bg)]",
  medium: "border-[var(--medium)] bg-[var(--medium-bg)]",
  low: "border-[var(--low)] bg-[var(--low-bg)]",
};
const BADGE: Record<Severity, string> = {
  high: "text-[var(--high)]",
  medium: "text-[var(--medium)]",
  low: "text-[var(--low)]",
};
const ICON: Record<Severity, string> = { high: "⚠️", medium: "❗", low: "ℹ️" };

/** The scan's own Korean text. Shown only when the backend matched it to the scan. */
function Quote({ t, text, verified }: { t: Texts; text: string | null; verified: boolean }) {
  if (!text || !verified) return null;
  return (
    <blockquote lang="ko" className="mt-2 border-l-4 border-line bg-bg/60 px-3 py-2 text-sm">
      <span className="block text-xs font-medium text-muted">{t.original}</span>
      {text}
    </blockquote>
  );
}

function NumberWarning({ t, ok }: { t: Texts; ok: boolean }) {
  return ok ? null : <p className="mt-2 text-sm font-medium text-[var(--medium)]">⚠ {t.unverifiedNumber}</p>;
}

interface Props {
  t: Texts;
  result: Explanation;
  onDelete: () => void;
  onNew: () => void;
}

export default function ResultView({ t, result, onDelete, onNew }: Props) {
  const flags = sortFlags(result.red_flags);

  return (
    <article className="space-y-6">
      {result.warnings.length > 0 && (
        <aside className="rounded-xl border border-[var(--medium)] bg-[var(--medium-bg)] p-4" role="note">
          <h2 className="font-semibold">{t.warnings}</h2>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </aside>
      )}

      <section>
        <h2 className="mb-2 text-lg font-semibold">{t.summary}</h2>
        <p className="whitespace-pre-line rounded-xl border border-line bg-card p-4">{result.summary}</p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">{t.redFlags}</h2>
        {flags.length === 0 ? (
          <p className="rounded-xl border border-line bg-card p-4 text-sm">{t.noRedFlags}</p>
        ) : (
          <ul className="space-y-3">
            {flags.map((f, i) => (
              <li key={i} className={`rounded-xl border-l-4 p-4 ${STYLE[f.severity]}`}>
                <p className={`text-xs font-bold uppercase tracking-wide ${BADGE[f.severity]}`}>
                  {ICON[f.severity]} {t.severity[f.severity]}
                </p>
                <h3 className="mt-1 font-semibold">{f.title}</h3>
                <p className="mt-1 whitespace-pre-line text-sm">{f.explanation}</p>
                <Quote t={t} text={f.original_text} verified={f.quote_verified} />
                <NumberWarning t={t} ok={f.numbers_verified} />
              </li>
            ))}
          </ul>
        )}
      </section>

      {result.key_facts.length > 0 && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">{t.keyFacts}</h2>
          <dl className="divide-y divide-line rounded-xl border border-line bg-card">
            {result.key_facts.map((k, i) => (
              <div key={i} className="p-3">
                <dt className="text-sm text-muted">{k.label}</dt>
                <dd className="font-medium">{k.value}</dd>
                <Quote t={t} text={k.original_text} verified={k.quote_verified} />
                <NumberWarning t={t} ok={k.numbers_verified} />
              </div>
            ))}
          </dl>
        </section>
      )}

      {result.todos.length > 0 && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">{t.todos}</h2>
          <ul className="space-y-2">
            {result.todos.map((d, i) => (
              <li key={i} className="flex gap-3 rounded-xl border border-line bg-card p-3">
                <span aria-hidden>☐</span>
                <span>
                  {d.action}
                  {d.deadline && (
                    <span className="block text-sm text-muted">
                      {t.deadline}: {d.deadline}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="rounded-xl border border-line p-4 text-sm text-muted">{result.disclaimer}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <button type="button" onClick={onNew} className="rounded-xl bg-brand px-4 font-semibold text-brand-ink">
          {t.newDocument}
        </button>
        <button type="button" onClick={onDelete} className="rounded-xl border border-line px-4 font-medium">
          🗑 {t.deleteResult}
        </button>
      </div>
    </article>
  );
}
