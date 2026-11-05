"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { guessLang, LANG_NAMES, TEXTS } from "@/lib/i18n";
import { LANGS, type Lang } from "@/lib/types";

const LANG_KEY = "clearko.lang"; // same key as the main page

export default function Privacy() {
  const [lang, setLang] = useState<Lang>("en");
  const [where, setWhere] = useState<"local" | "cloud" | "unknown">("unknown");
  const t = TEXTS[lang];

  useEffect(() => {
    let saved: string | null = null;
    try {
      saved = localStorage.getItem(LANG_KEY);
    } catch {}
    setLang(LANGS.includes(saved as Lang) ? (saved as Lang) : guessLang(navigator.languages ?? [navigator.language]));
    // ask the server where the text is processed; say nothing rather than guess if it is unreachable
    fetch(`${API_URL}/api/health`, { cache: "no-store" })
      .then((r) => r.json())
      .then((h) => setWhere(h.llm === "local" ? "local" : h.llm === "cloud" ? "cloud" : "unknown"))
      .catch(() => setWhere("unknown"));
  }, []);

  function choose(l: Lang) {
    setLang(l);
    try {
      localStorage.setItem(LANG_KEY, l);
    } catch {}
  }

  return (
    <main className="mx-auto w-full max-w-2xl space-y-6 px-4 pb-16 pt-6">
      <div className="flex items-center justify-between gap-3">
        <Link href="/" className="min-h-11 content-center font-medium text-brand underline">
          ← {t.back}
        </Link>
        <div role="group" aria-label={t.language} className="flex overflow-hidden rounded-xl border border-line bg-card">
          {LANGS.map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => choose(l)}
              aria-pressed={l === lang}
              className={`min-h-11 px-3 text-sm font-medium ${l === lang ? "bg-brand text-brand-ink" : "text-ink"}`}
            >
              {LANG_NAMES[l]}
            </button>
          ))}
        </div>
      </div>

      <h1 className="text-2xl font-bold tracking-tight">{t.privacyTitle}</h1>

      {where !== "unknown" && (
        <p
          className={`rounded-xl border p-4 text-sm font-medium ${
            where === "cloud" ? "border-[var(--medium)] bg-[var(--medium-bg)]" : "border-line bg-card"
          }`}
        >
          {where === "local" ? t.privacyLocal : t.privacyCloud}
        </p>
      )}

      <ul className="list-disc space-y-3 pl-5">
        {t.privacyPoints.map((p, i) => (
          <li key={i}>{p}</li>
        ))}
      </ul>
    </main>
  );
}
