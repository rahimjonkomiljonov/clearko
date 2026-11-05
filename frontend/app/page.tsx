"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ResultView from "@/components/ResultView";
import Uploader from "@/components/Uploader";
import Working from "@/components/Working";
import { ClearKoError, deleteJob, startJob, waitForJob } from "@/lib/api";
import { checkFile, checkSelection } from "@/lib/files";
import { errorText, guessLang, LANG_NAMES, TEXTS } from "@/lib/i18n";
import { LANGS, type DocType, type Explanation, type Lang } from "@/lib/types";

type Phase =
  | { kind: "pick" }
  | { kind: "uploading" }
  | { kind: "working"; jobId: string; status: string; stage: string }
  | { kind: "done"; jobId: string; result: Explanation }
  | { kind: "deleted" };

interface Problem {
  code: string;
  message: string;
  retryAfter?: number;
}

const LANG_KEY = "clearko.lang";

export default function Home() {
  const [lang, setLang] = useState<Lang>("en");
  const [phase, setPhase] = useState<Phase>({ kind: "pick" });
  const [files, setFiles] = useState<File[]>([]);
  const [docType, setDocType] = useState<DocType | "auto">("auto");
  const [problem, setProblem] = useState<Problem | null>(null);
  const abort = useRef<AbortController | null>(null);
  const jobId = useRef<string | null>(null);
  const t = TEXTS[lang];

  // remembered language, else the browser's (storage can be blocked: never let that break the page)
  useEffect(() => {
    let saved: string | null = null;
    try {
      saved = localStorage.getItem(LANG_KEY);
    } catch {}
    setLang(LANGS.includes(saved as Lang) ? (saved as Lang) : guessLang(navigator.languages ?? [navigator.language]));
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // leaving the page: ask the server to delete any result right away (best effort)
  useEffect(() => {
    const bye = () => {
      if (jobId.current) void deleteJob(jobId.current);
    };
    window.addEventListener("pagehide", bye);
    return () => window.removeEventListener("pagehide", bye);
  }, []);

  function chooseLang(l: Lang) {
    setLang(l);
    try {
      localStorage.setItem(LANG_KEY, l);
    } catch {}
  }

  const fail = useCallback((e: unknown, l: Lang) => {
    if (e instanceof DOMException && e.name === "AbortError") return;
    const err = e instanceof ClearKoError ? e : new ClearKoError("internal", "");
    // the API's message is in the language the job was sent with; ours covers the rest
    setProblem({ code: err.code, message: err.message || TEXTS[l].errors[err.code] || "", retryAfter: err.retryAfter });
    jobId.current = null;
    setPhase({ kind: "pick" });
  }, []);

  function add(list: File[]) {
    const bad = list.map(checkFile).find(Boolean);
    const next = [...files, ...list.filter((f) => !checkFile(f))];
    const sel = next.length ? checkSelection(next) : null;
    const code = bad ?? sel;
    setProblem(code ? { code, message: "" } : null);
    setFiles(code === "too_many" ? files : next);
  }

  async function submit() {
    const code = checkSelection(files);
    if (code) return setProblem({ code, message: "" });
    setProblem(null);
    setPhase({ kind: "uploading" });
    const sent = lang;
    const ctl = new AbortController();
    abort.current = ctl;
    try {
      const id = await startJob(files, sent, docType === "auto" ? undefined : docType);
      jobId.current = id;
      setPhase({ kind: "working", jobId: id, status: "queued", stage: "queued" });
      const final = await waitForJob(
        id,
        (s) => setPhase({ kind: "working", jobId: id, status: s.status, stage: s.stage }),
        ctl.signal,
      );
      if (final.status === "failed" && final.error) {
        throw new ClearKoError(final.error.code, final.error.message);
      }
      if (final.result) {
        setFiles([]); // the photos are not needed any more
        setPhase({ kind: "done", jobId: id, result: final.result });
      }
    } catch (e) {
      fail(e, sent);
    }
  }

  function cancel() {
    abort.current?.abort();
    if (jobId.current) void deleteJob(jobId.current);
    jobId.current = null;
    setPhase({ kind: "pick" });
  }

  function remove() {
    if (jobId.current) void deleteJob(jobId.current);
    jobId.current = null;
    setPhase({ kind: "deleted" });
  }

  function again() {
    if (jobId.current) void deleteJob(jobId.current);
    jobId.current = null;
    setFiles([]);
    setProblem(null);
    setPhase({ kind: "pick" });
  }

  return (
    <main className="mx-auto w-full max-w-2xl space-y-6 px-4 pb-16 pt-6">
      <header className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight">ClearKo</h1>
          <div role="group" aria-label={t.language} className="flex overflow-hidden rounded-xl border border-line bg-card">
            {LANGS.map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => chooseLang(l)}
                aria-pressed={l === lang}
                disabled={phase.kind === "uploading" || phase.kind === "working"}
                className={`min-h-11 px-3 text-sm font-medium ${
                  l === lang ? "bg-brand text-brand-ink" : "text-ink"
                } disabled:opacity-60`}
              >
                {LANG_NAMES[l]}
              </button>
            ))}
          </div>
        </div>
        <p className="text-muted">{t.tagline}</p>
        <p className="rounded-lg border border-line bg-card px-3 py-2 text-sm">{t.disclaimerShort}</p>
      </header>

      {problem && (
        <div role="alert" className="rounded-xl border border-[var(--high)] bg-[var(--high-bg)] p-4">
          <p className="font-medium">{errorText(t, problem.code, problem.message)}</p>
          {problem.retryAfter && <p className="mt-1 text-sm">{t.retryIn(problem.retryAfter)}</p>}
        </div>
      )}

      {(phase.kind === "pick" || phase.kind === "uploading") && (
        <Uploader
          t={t}
          files={files}
          docType={docType}
          busy={phase.kind === "uploading"}
          onAdd={add}
          onRemove={(i) => setFiles(files.filter((_, j) => j !== i))}
          onDocType={setDocType}
          onSubmit={submit}
        />
      )}

      {phase.kind === "working" && <Working t={t} status={phase.status} stage={phase.stage} onCancel={cancel} />}

      {phase.kind === "done" && <ResultView t={t} result={phase.result} onDelete={remove} onNew={again} />}

      {phase.kind === "deleted" && (
        <section className="space-y-4 rounded-2xl border border-line bg-card p-5">
          <p className="font-medium">{t.deleted}</p>
          <button type="button" onClick={again} className="w-full rounded-xl bg-brand px-4 font-semibold text-brand-ink">
            {t.newDocument}
          </button>
        </section>
      )}

      <footer className="text-center text-xs text-muted">{t.privacy}</footer>
    </main>
  );
}
