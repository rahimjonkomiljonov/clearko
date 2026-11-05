"""Jobs: an analysis takes 45-100 s, so the API returns a job id and the app polls.

Everything lives in memory and expires: uploaded pages are dropped as soon as the worker has
read them, results are deleted after `ttl_s` (or when the app asks). Nothing is written to disk.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("clearko.jobs")

QUEUED, RUNNING, DONE, FAILED = "queued", "running", "done", "failed"


@dataclass
class Job:
    id: str
    lang: str
    status: str = QUEUED
    stage: str = "queued"
    result: dict[str, Any] | None = None
    error_code: str | None = None
    created: float = 0.0
    finished: float | None = None


class QueueFull(Exception):
    pass


class JobManager:
    """One worker thread: OCR and the LLM share one GPU, so analyses run one at a time."""

    def __init__(self, ttl_s: int, max_queue: int, clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_s
        self._max_queue = max_queue
        self._clock = clock
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clearko-worker")

    def submit(self, lang: str, work: Callable[[Callable[[str], None]], dict[str, Any]],
               classify_error: Callable[[Exception], str]) -> Job:
        """`work(on_stage)` returns the result dict; `classify_error` maps an exception to a code."""
        with self._lock:
            self._purge_locked()
            waiting = sum(j.status in (QUEUED, RUNNING) for j in self._jobs.values())
            if waiting > self._max_queue:
                raise QueueFull
            job = Job(secrets.token_urlsafe(16), lang, created=self._clock())
            self._jobs[job.id] = job
        self._pool.submit(self._run, job, work, classify_error)
        return job

    def _run(self, job: Job, work, classify_error) -> None:  # type: ignore[no-untyped-def]
        job.status, job.stage = RUNNING, "starting"

        def on_stage(stage: str) -> None:
            job.stage = stage

        try:
            job.result = work(on_stage)
            job.status, job.stage = DONE, "done"
        except Exception as e:  # noqa: BLE001  any failure must end the job, not the worker
            job.error_code = classify_error(e)
            job.status, job.stage = FAILED, "failed"
            # type only: exception messages could contain document text
            log.warning("job %s failed: %s (%s)", job.id[:6], job.error_code, type(e).__name__)
        finally:
            job.finished = self._clock()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._purge_locked()
            return self._jobs.get(job_id)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None

    def _purge_locked(self) -> None:
        now = self._clock()
        old = [
            k for k, j in self._jobs.items()
            if j.finished is not None and now - j.finished > self._ttl
        ]
        for k in old:
            del self._jobs[k]

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
