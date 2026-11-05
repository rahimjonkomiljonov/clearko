import type { ApiError, DocType, JobStatus, Lang } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** An error the API (or the network) reported; `code` matches backend/app/messages.py. */
export class ClearKoError extends Error {
  constructor(
    public code: string,
    message: string,
    public retryAfter?: number,
  ) {
    super(message);
  }
}

async function failure(res: Response): Promise<ClearKoError> {
  let err: ApiError | null = null;
  try {
    const body = await res.json();
    if (body?.detail?.code) err = body.detail as ApiError;
  } catch {
    // not JSON (a proxy error page, for instance)
  }
  const retry = Number(res.headers.get("retry-after")) || undefined;
  return new ClearKoError(err?.code ?? "internal", err?.message ?? "", retry);
}

async function call(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new ClearKoError("network", "");
  }
}

export async function startJob(files: File[], lang: Lang, docType?: DocType): Promise<string> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  form.append("lang", lang);
  if (docType) form.append("doc_type", docType);
  const res = await call(`${API_URL}/api/jobs`, { method: "POST", body: form });
  if (!res.ok) throw await failure(res);
  return (await res.json()).job_id as string;
}

export async function getJob(id: string, signal?: AbortSignal): Promise<JobStatus> {
  const res = await call(`${API_URL}/api/jobs/${encodeURIComponent(id)}`, { cache: "no-store", signal });
  if (!res.ok) throw await failure(res);
  return (await res.json()) as JobStatus;
}

/** Deletes the result on the server. Best effort: a failure is not shown to the user. */
export async function deleteJob(id: string): Promise<void> {
  try {
    await fetch(`${API_URL}/api/jobs/${encodeURIComponent(id)}`, { method: "DELETE", keepalive: true });
  } catch {
    // the result expires on its own after 15 minutes
  }
}

/** Polls until the job is done or failed. `onUpdate` gets every status. */
export async function waitForJob(
  id: string,
  onUpdate: (s: JobStatus) => void,
  signal: AbortSignal,
  intervalMs = 1500,
): Promise<JobStatus> {
  let misses = 0;
  for (;;) {
    if (signal.aborted) throw new DOMException("aborted", "AbortError");
    try {
      const s = await getJob(id, signal);
      misses = 0;
      onUpdate(s);
      if (s.status === "done" || s.status === "failed") return s;
    } catch (e) {
      if (signal.aborted) throw e;
      // a lost connection on a phone is normal: retry a few times before giving up
      if (e instanceof ClearKoError && e.code === "network" && ++misses < 5) {
        // fall through to the sleep below
      } else {
        throw e;
      }
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
