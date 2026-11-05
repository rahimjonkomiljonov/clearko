// The API reports a free-text `stage`; turn it into a step and a rough percentage.

export type StepKey = "queued" | "reading" | "summarizing" | "reviewing" | "translating" | "done";

export interface Progress {
  step: StepKey;
  /** 0-100, only a hint for the progress bar */
  percent: number;
  /** "2/6" style detail when the stage has one */
  detail: string | null;
}

export const STEPS: StepKey[] = ["reading", "summarizing", "reviewing", "translating"];

// Where each step starts and how wide it is on the bar (the review is the longest).
const SPAN: Record<StepKey, [number, number]> = {
  queued: [2, 0],
  reading: [5, 15],
  summarizing: [20, 15],
  reviewing: [35, 45],
  translating: [80, 18],
  done: [100, 0],
};

function fraction(stage: string): [number, number] | null {
  const m = stage.match(/(\d+)\s*\/\s*(\d+)/);
  if (!m) return null;
  const n = Number(m[1]);
  const total = Number(m[2]);
  return total > 0 ? [Math.min(n, total), total] : null;
}

export function parseStage(status: string, stage: string): Progress {
  if (status === "done") return { step: "done", percent: 100, detail: null };
  const s = stage.toLowerCase();
  let step: StepKey = "queued";
  if (s.startsWith("page ") || s === "starting") step = "reading";
  else if (s.startsWith("summariz")) step = "summarizing";
  else if (s.startsWith("reviewing")) step = "reviewing";
  else if (s.startsWith("translating")) step = "translating";

  const frac = step === "reviewing" || step === "translating" || step === "reading" ? fraction(s) : null;
  const [start, width] = SPAN[step];
  const percent = frac ? start + (width * frac[0]) / frac[1] : start;
  return { step, percent: Math.round(percent), detail: frac ? `${frac[0]}/${frac[1]}` : null };
}
