"""ClearKo HTTP API.

    POST   /api/jobs        upload page(s) + lang  -> 202 {job_id}   (validates, then queues)
    GET    /api/jobs/{id}   status / stage / result or error
    DELETE /api/jobs/{id}   delete the result now
    GET    /api/health

Run:  python -m uvicorn app.api.main:app --port 8000

Privacy: pages are decoded in memory and dropped when the analysis ends; results are kept in
memory for `job_ttl_s` and deleted; nothing is written to disk by ClearKo (the web framework may
spool large uploads to a temp file for the length of one request) and no document text is logged.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..explain import DocType, LLMClient, LLMError, get_llm_client
from ..explain.nllb import NLLBUnavailable
from ..explain.parse import ParseError
from ..explain.translate import StringTranslator
from ..explain.translators import get_translator
from ..messages import message
from ..ocr import OCREngine, get_engine
from ..pipeline import NoTextFound, Page, UnsupportedDocument, analyze, pages_from_bytes
from ..preprocess import BlurryImageError
from .jobs import DONE, FAILED, Job, JobManager, QueueFull
from .limits import RateLimiter

log = logging.getLogger("clearko.api")
LANGS = ("uz", "ru", "en")
_HEIC_BRANDS = (b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1")


@dataclass
class Services:
    """The heavy parts, built once: OCR models, the LLM client and the translator choice."""

    engine: OCREngine
    llm: LLMClient
    translator_for: Callable[[str], LLMClient | StringTranslator | None]


class ErrorOut(BaseModel):
    code: str
    message: str


class JobOut(BaseModel):
    job_id: str
    status: str
    stage: str
    result: dict[str, Any] | None = None
    error: ErrorOut | None = None


def sniff(data: bytes) -> str | None:
    """File type from the first bytes (the extension and Content-Type are not trusted)."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data[4:8] == b"ftyp" and data[8:12] in _HEIC_BRANDS:
        return "heic"
    return None


def classify_error(e: Exception) -> str:
    if isinstance(e, BlurryImageError):
        return "blurry"
    if isinstance(e, NoTextFound):
        return "no_text"
    if isinstance(e, UnsupportedDocument):
        return "unsupported"
    if isinstance(e, (LLMError, ParseError, NLLBUnavailable)):
        return "explain_failed"
    return "internal"


def client_key(request: Request, trust_proxy: bool) -> str:
    if trust_proxy and (fwd := request.headers.get("x-forwarded-for")):
        # A client can put anything at the START of this header; the LAST entry is the one the
        # (single) trusted proxy added, so that is the only one to believe.
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def fail(status: int, code: str, lang: str = "en", headers: dict[str, str] | None = None,
         **fmt: object) -> HTTPException:
    detail = {"code": code, "message": message(code, lang, **fmt)}
    return HTTPException(status_code=status, detail=detail, headers=headers)


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    cfg = settings or get_settings()
    jobs = JobManager(cfg.job_ttl_s, cfg.max_queue)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        jobs.shutdown()

    app = FastAPI(title="ClearKo", docs_url=None, redoc_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cfg.cors_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    per_client = RateLimiter([(cfg.rate_per_hour, 3600), (cfg.rate_per_day, 86400)])
    overall = RateLimiter([(cfg.global_per_day, 86400)])
    built: list[Services] = [services] if services else []
    build_lock = threading.Lock()

    def get_services() -> Services:  # first call loads the OCR models (~10-20 s)
        with build_lock:
            if not built:
                llm = get_llm_client(
                    cfg.llm_provider, cfg.llm_api_key, cfg.llm_model, cfg.llm_base_url
                )
                built.append(Services(
                    get_engine(cfg.ocr_engine, cfg.ocr_device), llm,
                    lambda lang: get_translator(lang, cfg),
                ))
            return built[0]

    @app.get("/api/health")
    def health() -> dict[str, str]:
        # `llm` tells the privacy page whether documents stay on this server ("local") or the
        # text is sent to a cloud model ("cloud"); never say "local" when it is not true.
        return {"status": "ok", "llm": "local" if cfg.llm_provider == "ollama" else "cloud"}

    @app.post("/api/jobs", status_code=202)
    async def create_job(
        request: Request,
        files: Annotated[list[UploadFile] | None, File()] = None,
        lang: Annotated[str, Form()] = "en",
        doc_type: Annotated[str | None, Form()] = None,
    ) -> dict[str, str]:
        if lang not in LANGS:
            raise fail(400, "bad_lang")
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > (cfg.max_total_mb + 2) * 1024 * 1024:
            raise fail(413, "too_large", lang)
        for limiter in (per_client, overall):
            key = client_key(request, cfg.trust_proxy) if limiter is per_client else "all"
            wait = limiter.check(key)
            if wait is not None:
                code = "rate_limited" if limiter is per_client else "busy"
                raise fail(429, code, lang, {"Retry-After": str(int(wait) + 1)})
        if not files:
            raise fail(400, "no_files", lang)
        if len(files) > cfg.max_files:
            raise fail(400, "too_many", lang, n=cfg.max_pages)

        pages: list[Page] = []
        total = 0
        for n, f in enumerate(files, 1):
            data = await _read_capped(f, cfg.max_file_mb * 1024 * 1024)
            if data is None:
                raise fail(413, "too_large", lang)
            total += len(data)
            if total > cfg.max_total_mb * 1024 * 1024:
                raise fail(413, "too_large", lang)
            kind = sniff(data)
            if kind == "heic":
                raise fail(400, "heic", lang)
            if kind is None:
                raise fail(400, "bad_file", lang)
            try:
                pages += await run_in_threadpool(pages_from_bytes, f"upload{n}", data)
            except Exception as e:  # noqa: BLE001  corrupt image/PDF: say so, never echo content
                log.info("unreadable upload: %s", type(e).__name__)
                raise fail(400, "bad_file", lang) from None
            del data
        if len(pages) > cfg.max_pages:
            raise fail(400, "too_many", lang, n=cfg.max_pages)

        chosen = None
        if doc_type:
            try:
                chosen = DocType(doc_type)
            except ValueError:
                raise fail(400, "bad_request", lang) from None
            if chosen == DocType.UNSUPPORTED:
                raise fail(400, "bad_request", lang)

        def work(on_stage: Callable[[str], None]) -> dict[str, Any]:
            try:
                svc = get_services()
                result, reading = analyze(
                    pages, lang, svc.engine, svc.llm, doc_type=chosen,
                    max_side=cfg.max_image_side, blur_threshold=cfg.blur_threshold,
                    translator=svc.translator_for(lang), on_stage=on_stage,
                )
                log.info("job done: type=%s pages=%d timings=%s", result.doc_type.value,
                         reading.pages, {k: round(v, 1) for k, v in reading.timings.items()})
                return result.model_dump(mode="json")
            finally:
                pages.clear()  # drop the uploaded images as soon as the analysis is over

        try:
            job = jobs.submit(lang, work, classify_error)
        except QueueFull:
            pages.clear()
            raise fail(503, "busy", lang, {"Retry-After": "60"}) from None
        return {"job_id": job.id, "status": job.status}

    def render(job: Job) -> JobOut:
        error = None
        if job.status == FAILED:
            code = job.error_code or "internal"
            error = ErrorOut(code=code, message=message(code, job.lang))
        return JobOut(
            job_id=job.id, status=job.status, stage=job.stage,
            result=job.result if job.status == DONE else None, error=error,
        )

    @app.get("/api/jobs/{job_id}", response_model=JobOut)
    def get_job(job_id: str, response: Response) -> JobOut:
        response.headers["Cache-Control"] = "no-store"
        job = jobs.get(job_id)
        if job is None:
            raise fail(404, "not_found")
        return render(job)

    @app.delete("/api/jobs/{job_id}", status_code=204)
    def delete_job(job_id: str) -> Response:
        jobs.delete(job_id)  # unknown ids are fine: the goal (no result stored) is met
        return Response(status_code=204)

    return app


async def _read_capped(f: UploadFile, limit: int) -> bytes | None:
    """Read an upload, giving up (None) as soon as it is bigger than `limit`."""
    buf = bytearray()
    while chunk := await f.read(1 << 20):
        buf += chunk
        if len(buf) > limit:
            return None
    return bytes(buf)


app = create_app()
