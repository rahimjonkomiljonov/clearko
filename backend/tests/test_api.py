"""API tests with a fake OCR engine and a fake LLM: no models, no GPU."""

import threading
import time

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.api.jobs import DONE, JobManager
from app.api.limits import RateLimiter
from app.api.main import Services, create_app, sniff
from app.config import Settings
from app.messages import MESSAGES
from app.ocr.base import OCREngine, OCRLine, OCRResult
from tests.test_clause_review import CONTRACT, RoutingLLM


class FakeEngine(OCREngine):
    name = "fake"

    def __init__(self, text=CONTRACT):
        self.text = text

    def recognize(self, image):
        lines = [OCRLine(t, 0.95, (0, 20 * i, 200, 20 * i + 15))
                 for i, t in enumerate(self.text.splitlines()) if t.strip()]
        return OCRResult(lines)


def png(textured=True) -> bytes:
    rng = np.random.default_rng(1)
    img = (rng.integers(0, 255, (300, 200, 3), dtype=np.uint8) if textured
           else np.full((300, 200, 3), 128, np.uint8))
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def make_client(llm=None, engine=None, **overrides):
    settings = Settings(_env_file=None, **overrides)
    services = Services(engine or FakeEngine(), llm or RoutingLLM(), lambda lang: None)
    return TestClient(create_app(settings, services))


def post(client, data=None, lang="en", doc_type="rental", n=1):
    files = [("files", (f"p{i}.png", data or png(), "image/png")) for i in range(n)]
    form = {"lang": lang}
    if doc_type:
        form["doc_type"] = doc_type
    return client.post("/api/jobs", files=files, data=form)


def wait(client, job_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        body = client.get(f"/api/jobs/{job_id}").json()
        if body["status"] in ("done", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("job did not finish")


# ---------- happy path ----------
def test_health():
    assert make_client().get("/api/health").json() == {"status": "ok", "llm": "local"}


def test_health_says_cloud_when_a_cloud_model_is_configured():
    assert make_client(llm_provider="gemini").get("/api/health").json()["llm"] == "cloud"


def test_health_says_cloud_when_pages_go_to_a_cloud_ocr_even_with_a_local_llm():
    assert make_client(ocr_engine="gemini").get("/api/health").json()["llm"] == "cloud"


def test_responses_carry_security_headers_and_are_not_cached():
    r = make_client().get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_upload_then_poll_gives_the_explanation():
    c = make_client()
    r = post(c)
    assert r.status_code == 202
    body = wait(c, r.json()["job_id"])
    assert body["status"] == "done" and body["error"] is None
    assert body["result"]["doc_type"] == "rental"
    assert body["result"]["disclaimer"]
    assert "보증금" in body["result"]["ocr_text"]  # the scan is returned for the collapsible view
    assert any(f["severity"] == "high" for f in body["result"]["red_flags"])


def test_result_can_be_deleted_and_is_then_gone():
    c = make_client()
    job_id = post(c).json()["job_id"]
    wait(c, job_id)
    assert c.delete(f"/api/jobs/{job_id}").status_code == 204
    assert c.get(f"/api/jobs/{job_id}").status_code == 404


def test_unknown_job_is_404():
    r = make_client().get("/api/jobs/nope")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_found"


# ---------- bad input ----------
def test_unknown_language_is_rejected():
    r = post(make_client(), lang="de")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_lang"


def test_no_files_is_a_friendly_400():
    r = make_client().post("/api/jobs", data={"lang": "en"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "no_files"


def test_text_file_is_rejected_whatever_its_name_says():
    r = post(make_client(), data=b"hello, I am not an image at all")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_file"


def test_heic_gets_its_own_message():
    heic = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 50
    r = post(make_client(), data=heic)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "heic"


def test_corrupt_image_is_rejected():
    r = post(make_client(), data=b"\x89PNG\r\n\x1a\n" + b"garbage" * 20)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_file"


def test_oversized_file_is_413():
    r = post(make_client(max_file_mb=1), data=b"\x89PNG\r\n\x1a\n" + b"\0" * 1_200_000)
    assert r.status_code == 413 and r.json()["detail"]["code"] == "too_large"


def test_too_many_pages_is_rejected():
    r = post(make_client(max_pages=2), n=3)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "too_many"


def test_invalid_doc_type_is_rejected():
    r = post(make_client(), doc_type="mortgage")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_request"


# ---------- failures inside the pipeline are reported in the user's language ----------
def test_blurry_photo_fails_the_job_with_a_localised_message():
    c = make_client()
    job_id = post(c, data=png(textured=False), lang="ru").json()["job_id"]
    body = wait(c, job_id)
    assert body["status"] == "failed" and body["error"]["code"] == "blurry"
    assert body["error"]["message"] == MESSAGES["ru"]["blurry"]
    assert body["result"] is None


def test_unrelated_text_is_unsupported():
    c = make_client(engine=FakeEngine("The weather today is sunny with a light breeze from the sea"))
    body = wait(c, post(c, doc_type=None).json()["job_id"])
    assert body["error"]["code"] == "unsupported"


def test_llm_failure_is_reported_not_raised():
    from app.explain import LLMClient, LLMError

    class Down(LLMClient):
        def generate(self, system, messages, json_schema=None):
            raise LLMError("model server is down")

    c = make_client(llm=Down())
    body = wait(c, post(c).json()["job_id"])
    assert body["error"]["code"] == "explain_failed"
    assert "down" not in body["error"]["message"]  # internals are not shown


# ---------- limits ----------
def test_rate_limit_returns_429_with_retry_after_in_the_users_language():
    c = make_client(rate_per_hour=2)
    assert post(c).status_code == 202 and post(c).status_code == 202
    r = post(c, lang="uz")
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    assert r.json()["detail"]["message"] == MESSAGES["uz"]["rate_limited"]


def test_global_daily_cap_applies_to_everyone():
    c = make_client(global_per_day=1)
    assert post(c).status_code == 202
    r = post(c)
    assert r.status_code == 429 and r.json()["detail"]["code"] == "busy"


def test_full_queue_returns_503():
    release = threading.Event()

    class Slow(RoutingLLM):
        def generate(self, system, messages, json_schema=None):
            release.wait(10)
            return super().generate(system, messages, json_schema)

    c = make_client(llm=Slow(), max_queue=0, rate_per_hour=50)
    try:
        assert post(c).status_code == 202
        r = post(c)
        assert r.status_code == 503 and r.json()["detail"]["code"] == "busy"
    finally:
        release.set()


def test_forged_forwarded_for_does_not_dodge_the_rate_limit_behind_a_proxy():
    c = make_client(rate_per_hour=1, trust_proxy=True)

    def send(forged):
        files = [("files", ("p.png", png(), "image/png"))]
        headers = {"x-forwarded-for": f"{forged}, 203.0.113.9"}  # last entry = added by the proxy
        return c.post("/api/jobs", files=files, data={"lang": "en", "doc_type": "rental"}, headers=headers)

    assert send("1.1.1.1").status_code == 202
    assert send("2.2.2.2").status_code == 429  # same real client, different forged prefix


def test_without_trust_proxy_the_header_is_ignored():
    c = make_client(rate_per_hour=1, trust_proxy=False)
    h = {"x-forwarded-for": "9.9.9.9"}
    files = lambda: [("files", ("p.png", png(), "image/png"))]
    assert c.post("/api/jobs", files=files(), headers=h, data={"lang": "en"}).status_code == 202
    h = {"x-forwarded-for": "8.8.8.8"}
    assert c.post("/api/jobs", files=files(), headers=h, data={"lang": "en"}).status_code == 429


# ---------- units ----------
def test_rate_limiter_sliding_window():
    now = [0.0]
    lim = RateLimiter([(2, 10)], clock=lambda: now[0])
    assert lim.check("a") is None and lim.check("a") is None
    wait_s = lim.check("a")
    assert wait_s is not None and 0 < wait_s <= 10
    assert lim.check("b") is None  # other clients are unaffected
    now[0] = 11
    assert lim.check("a") is None


def test_rate_limiter_checks_every_window():
    now = [0.0]
    lim = RateLimiter([(5, 10), (6, 100)], clock=lambda: now[0])
    for i in range(5):
        now[0] = i
        assert lim.check("a") is None
    now[0] = 20  # the short window is clear, the long one has 5 of 6 used
    assert lim.check("a") is None
    assert lim.check("a") is not None


def test_sniff_recognises_formats_by_content():
    assert sniff(b"\xff\xd8\xff\xe0" + b"0" * 20) == "jpeg"
    assert sniff(b"%PDF-1.7 ...") == "pdf"
    assert sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "webp"
    assert sniff(b"plain text") is None


def test_finished_jobs_expire():
    now = [0.0]
    mgr = JobManager(ttl_s=100, max_queue=2, clock=lambda: now[0])
    job = mgr.submit("en", lambda on_stage: {"ok": True}, lambda e: "internal")
    end = time.time() + 5
    while job.status != DONE and time.time() < end:
        time.sleep(0.01)
    assert mgr.get(job.id) is not None
    now[0] = 101
    assert mgr.get(job.id) is None
    mgr.shutdown()
