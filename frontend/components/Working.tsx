"use client";

import type { Texts } from "@/lib/i18n";
import { parseStage, STEPS } from "@/lib/progress";

interface Props {
  t: Texts;
  status: string;
  stage: string;
  onCancel: () => void;
}

export default function Working({ t, status, stage, onCancel }: Props) {
  const p = parseStage(status, stage);
  const current = STEPS.indexOf(p.step as (typeof STEPS)[number]);

  return (
    <section className="space-y-5 rounded-2xl border border-line bg-card p-5" aria-live="polite">
      <div>
        <h2 className="text-lg font-semibold">{t.working}</h2>
        <p className="text-sm text-muted">{t.waitHint}</p>
      </div>

      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={p.percent}
        className="h-2 overflow-hidden rounded-full bg-line"
      >
        <div className="h-full rounded-full bg-brand transition-all duration-700" style={{ width: `${p.percent}%` }} />
      </div>

      {p.step === "queued" ? (
        <p className="font-medium">{t.steps.queued}</p>
      ) : (
        <ol className="space-y-2">
          {STEPS.map((s, i) => {
            const state = i < current ? "done" : i === current ? "now" : "todo";
            return (
              <li key={s} className={state === "todo" ? "text-muted" : "font-medium"}>
                <span aria-hidden className="mr-2 inline-block w-5 text-center">
                  {state === "done" ? "✓" : state === "now" ? "●" : "○"}
                </span>
                {t.steps[s]}
                {state === "now" && p.detail ? ` (${p.detail})` : ""}
              </li>
            );
          })}
        </ol>
      )}

      <button type="button" onClick={onCancel} className="w-full rounded-xl border border-line px-4 font-medium">
        {t.cancel}
      </button>
    </section>
  );
}
