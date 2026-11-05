import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.explain import LLMError, get_llm_client
from app.explain.llm_client import OllamaClient


def serve(status: int, payload: dict | str, captured: list):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            captured.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = payload if isinstance(payload, str) else json.dumps(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, *args):  # keep test output quiet
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"


def test_ollama_request_and_reply():
    seen: list = []
    server, url = serve(200, {"message": {"role": "assistant", "content": '{"summary": "ok"}'}}, seen)
    try:
        client = OllamaClient("qwen2.5:7b", url)
        schema = {"type": "object"}
        reply = client.generate("SYS", [("user", "hi"), ("model", "yo"), ("user", "again")], schema)
    finally:
        server.shutdown()
    assert reply == '{"summary": "ok"}'
    req = seen[0]
    assert req["model"] == "qwen2.5:7b" and req["stream"] is False
    assert req["format"] == schema
    assert [m["role"] for m in req["messages"]] == ["system", "user", "assistant", "user"]


def test_ollama_defaults_to_plain_json_format():
    seen: list = []
    server, url = serve(200, {"message": {"content": "{}"}}, seen)
    try:
        OllamaClient("m", url).generate("s", [("user", "x")])
    finally:
        server.shutdown()
    assert seen[0]["format"] == "json"


def test_missing_model_gives_a_helpful_error():
    server, url = serve(404, {"error": "model not found"}, [])
    try:
        with pytest.raises(LLMError, match="ollama pull qwen2.5:7b"):
            OllamaClient("qwen2.5:7b", url).generate("s", [("user", "x")])
    finally:
        server.shutdown()


def test_empty_reply_is_an_error():
    server, url = serve(200, {"message": {"content": "  "}}, [])
    try:
        with pytest.raises(LLMError, match="empty"):
            OllamaClient("m", url).generate("s", [("user", "x")])
    finally:
        server.shutdown()


def test_unreachable_server_error_has_no_document_text():
    with pytest.raises(LLMError, match="Is it running") as exc:
        OllamaClient("m", "http://127.0.0.1:9", timeout_s=2).generate("s", [("user", "SECRET TEXT")])
    assert "SECRET" not in str(exc.value)


def test_factory_defaults_to_local_and_rejects_unknown():
    assert isinstance(get_llm_client("ollama", model="m"), OllamaClient)
    with pytest.raises(ValueError):
        get_llm_client("nope")


def test_plain_text_mode_sends_no_format(monkeypatch):
    sent = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"message": {"content": "hello"}}'

    def fake_urlopen(req, timeout):
        sent.update(json.loads(req.data))
        return Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert OllamaClient("m", force_json=False).generate("s", [("user", "hi")]) == "hello"
    assert "format" not in sent
    OllamaClient("m").generate("s", [("user", "hi")])
    assert sent["format"] == "json"
