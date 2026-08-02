import json

import yt_scribe.summarise as summarise_module
from yt_scribe.summarise import summarise


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install_fake(monkeypatch, captured):
    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["headers"] = dict(request.header_items())
        return FakeResponse(
            {"choices": [{"message": {"content": "  要約  "}}]}
        )

    monkeypatch.setattr(summarise_module.urllib.request, "urlopen", fake_urlopen)


def test_returns_stripped_content(monkeypatch):
    captured = {}
    install_fake(monkeypatch, captured)
    assert summarise("body", "http://x/v1", "m", "p") == "要約"


def test_posts_to_the_chat_completions_path(monkeypatch):
    captured = {}
    install_fake(monkeypatch, captured)
    summarise("body", "http://x/v1", "m", "p")
    assert captured["url"] == "http://x/v1/chat/completions"
    assert captured["body"]["model"] == "m"
    assert captured["body"]["messages"][0]["content"] == "p"
    assert captured["body"]["messages"][1]["content"] == "body"


def test_input_is_truncated(monkeypatch):
    captured = {}
    install_fake(monkeypatch, captured)
    summarise("x" * 50, "http://x/v1", "m", "p", max_chars=10)
    assert captured["body"]["messages"][1]["content"] == "x" * 10


def test_api_key_is_sent_when_given(monkeypatch):
    captured = {}
    install_fake(monkeypatch, captured)
    summarise("body", "http://x/v1", "m", "p", api_key="secret")
    assert captured["headers"]["Authorization"] == "Bearer secret"
