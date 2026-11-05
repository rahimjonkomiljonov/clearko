// Quick checks before uploading, so a phone user does not wait for an upload just to be told
// "no". The server checks everything again (from the file contents); these only save time.

export const MAX_FILES = 10;
export const MAX_FILE_BYTES = 12 * 1024 * 1024;
export const MAX_TOTAL_BYTES = 40 * 1024 * 1024;
export const ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";

const OK_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const OK_EXT = /\.(jpe?g|png|webp|pdf)$/i;
const HEIC = /\.(heic|heif)$/i;

export interface Fileish {
  name: string;
  type: string;
  size: number;
}

/** An error code from lib/i18n errors, or null if the file is fine. */
export function checkFile(f: Fileish): string | null {
  if (f.type === "image/heic" || f.type === "image/heif" || HEIC.test(f.name)) return "heic";
  if (!OK_TYPES.includes(f.type) && !OK_EXT.test(f.name)) return "bad_file";
  if (f.size > MAX_FILE_BYTES) return "too_large";
  return null;
}

/** Check a whole selection (already chosen + newly added). */
export function checkSelection(files: Fileish[]): string | null {
  if (files.length === 0) return "no_files";
  if (files.length > MAX_FILES) return "too_many";
  let total = 0;
  for (const f of files) {
    const bad = checkFile(f);
    if (bad) return bad;
    total += f.size;
  }
  return total > MAX_TOTAL_BYTES ? "too_large" : null;
}
