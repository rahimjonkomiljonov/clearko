"""GeminiClient with a fake SDK: no key, no network."""

import pytest
from google import genai

from app.config import Settings
from app.explain import LLMError
from app.explain.llm_client import GeminiClient
from app.explain.translators import get_translator


class ApiErr(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


class Resp:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append((model, config))
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return Resp(out)


def make(monkeypatch, outcomes, **kw):
    models = FakeModels(outcomes)

    class FakeClient:
        def __init__(self, api_key):
            self.models = models

    monkeypatch.setattr(genai, "Client", FakeClient)
    now = [0.0]
    sleeps = []

    def sleep(s):
        sleeps.append(s)
        now[0] += s

    client = GeminiClient("key", "gemini-test", sleep=sleep, clock=lambda: now[0], **kw)
    return client, models, sleeps


def test_schema_is_passed_through_and_text_returned(monkeypatch):
    client, models, _ = make(monkeypatch, ['{"ok": true}'])
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    assert client.generate("sys", [("user", "hi")], schema) == '{"ok": true}'
    model, config = models.calls[0]
    assert model == "gemini-test" and config.response_json_schema == schema
    assert config.response_mime_type == "application/json"


def test_rate_limit_is_retried_with_a_wait(monkeypatch):
    client, models, sleeps = make(monkeypatch, [ApiErr(429), ApiErr(503), "{}"])
    assert client.generate("s", [("user", "x")]) == "{}"
    assert len(models.calls) == 3
    assert 15.0 in sleeps and 30.0 in sleeps


def test_gives_up_after_the_retries_without_leaking_content(monkeypatch):
    client, models, _ = make(monkeypatch, [ApiErr(429)] * 4, retries=3)
    with pytest.raises(LLMError) as e:
        client.generate("s", [("user", "SECRET DOCUMENT TEXT")])
    assert "429" in str(e.value) and "SECRET" not in str(e.value)
    assert len(models.calls) == 4


def test_a_client_error_is_not_retried(monkeypatch):
    client, models, _ = make(monkeypatch, [ApiErr(400), "{}"])
    with pytest.raises(LLMError):
        client.generate("s", [("user", "x")])
    assert len(models.calls) == 1


def test_calls_are_spaced_out_to_stay_under_the_per_minute_quota(monkeypatch):
    client, _, sleeps = make(monkeypatch, ["{}", "{}", "{}"], min_interval_s=4.0)
    for _ in range(3):
        client.generate("s", [("user", "x")])
    assert sleeps == [4.0, 4.0]  # the first call needs no wait


def test_empty_answer_is_an_error(monkeypatch):
    client, _, _ = make(monkeypatch, [""])
    with pytest.raises(LLMError):
        client.generate("s", [("user", "x")])


def test_missing_key_is_a_clear_error():
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        GeminiClient("", "m")


def test_cloud_provider_uses_the_main_model_for_translation_not_local_ones():
    cfg = Settings(_env_file=None, llm_provider="gemini", llm_translate_model="gemma3:4b",
                   uz_translator="nllb")
    assert get_translator("ru", cfg) is None
    assert get_translator("uz", cfg) is None


# ---------- Gemini as the OCR engine ----------
def test_ocr_engine_turns_the_transcription_into_ordered_lines(monkeypatch):
    import numpy as np

    from app.ocr.gemini_engine import GeminiOCREngine

    client, _, _ = make(monkeypatch, [])
    seen = {}

    def fake_transcribe(jpeg, instruction):
        seen["jpeg_magic"] = jpeg[:2]
        seen["instruction"] = instruction
        return "```text\n임대인 : 홍길동\n\n보증금 : 10,000,000원\n```"

    client.transcribe = fake_transcribe
    engine = GeminiOCREngine(client)
    result = engine.recognize(np.full((200, 100, 3), 255, np.uint8))
    assert [ln.text for ln in result.lines] == ["임대인 : 홍길동", "보증금 : 10,000,000원"]
    assert seen["jpeg_magic"] == b"\xff\xd8" and "do not translate" in seen["instruction"]
    assert result.lines[0].bbox[1] < result.lines[1].bbox[1]  # keeps the model's order
    assert engine.has_confidence is False


def test_pipeline_reports_no_ocr_confidence_for_an_engine_without_one():
    import numpy as np

    from app.ocr.base import OCREngine, OCRLine, OCRResult
    from app.pipeline import Page, read_pages

    class NoConf(OCREngine):
        name = "noconf"
        has_confidence = False

        def recognize(self, image):
            return OCRResult([OCRLine("보증금 : 10,000,000원", 1.0, (0, 0, 10, 10))])

    textured = np.random.default_rng(1).integers(0, 255, (300, 200, 3), dtype=np.uint8)
    reading = read_pages([Page("p", image=textured)], NoConf())
    assert reading.confidence is None and "보증금" in reading.text


def test_engine_from_settings_shares_the_llm_client(monkeypatch):
    from app.ocr import engine_from_settings

    client, _, _ = make(monkeypatch, [])
    cfg = Settings(_env_file=None, ocr_engine="gemini", llm_api_key="k")
    engine = engine_from_settings(cfg, client)
    assert engine.name == "gemini" and engine._client is client


def test_a_looping_transcription_is_cut_but_normal_repeats_stay():
    from app.ocr.gemini_engine import cap_repeats

    page = ["임대인 : 홍길동"] + ["년", "월", "일"] * 4 + ["보증금 : 1,000원"]  # 4 date fields: normal
    assert cap_repeats(page) == page
    loop = ["일까지 임차인의 전입신고를 받기로 하고"] * 147 + ["끝"]
    capped = cap_repeats(loop)
    assert capped.count("일까지 임차인의 전입신고를 받기로 하고") == 6 and capped[-1] == "끝"
