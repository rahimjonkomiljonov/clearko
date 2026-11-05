import type { RedFlag, Severity } from "./types";

const ORDER: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

/** Serious first; the sort is stable, so document order is kept inside a level. */
export function sortFlags(flags: RedFlag[]): RedFlag[] {
  return [...flags].sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);
}
