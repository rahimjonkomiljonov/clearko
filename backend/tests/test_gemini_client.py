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
