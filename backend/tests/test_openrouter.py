from types import SimpleNamespace

import pytest

from app.ai.factory import build_provider
from app.ai.jsonutil import extract_json_object
from app.ai.openrouter_provider import OpenRouterProvider
from app.core.config import OPENROUTER_BASE_URL, Settings
from backend.tests.conftest import settings


class _Completions:
    def __init__(self, contents: list[str]) -> None:
        self.contents = list(contents)
        self.kwargs: list[dict] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs.append(kwargs)
        content = self.contents.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_extracts_the_first_object() -> None:
    assert extract_json_object('texto {"a": 1, "b": "x{y}"} más') == {"a": 1, "b": "x{y}"}
    assert extract_json_object("sin json") is None


def test_openrouter_request_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict = {}
    completions = _Completions(['{"ok": true}'])

    class FakeOpenAI:
        def __init__(self, **kwargs: object) -> None:
            created.update(kwargs)
            self.chat = SimpleNamespace(completions=completions)

    monkeypatch.setattr("app.ai.openrouter_provider.OpenAI", FakeOpenAI)
    configured = settings(
        ai_enabled=True,
        ai_model="acme/modelo-sintetico",
        openrouter_api_key="sk-test-not-real",
        ai_temperature=None,
        ai_json_mode=True,
        openrouter_zdr=True,
        openrouter_app_title="Security Tech AI (personal)",
        ai_max_output_tokens=1234,
    )
    provider = OpenRouterProvider(configured)
    assert provider.complete_json("sistema", "usuario") == {"ok": True}
    assert created["base_url"] == OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
    assert created["max_retries"] == 0
    assert created["default_headers"]["X-OpenRouter-Title"] == "Security Tech AI (personal)"
    sent = completions.kwargs[0]
    assert sent["model"] == "acme/modelo-sintetico"
    assert "temperature" not in sent
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["extra_body"] == {"provider": {"zdr": True}}
    assert sent["max_tokens"] == 1234


def test_retries_once_when_the_text_is_not_json() -> None:
    completions = _Completions(["no es json", 'nota {"valor": 2}'])
    provider = OpenRouterProvider(
        settings(ai_enabled=True, ai_model="acme/modelo-sintetico", openrouter_api_key="sk-test-not-real", ai_temperature=0.2, openrouter_zdr=False),
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )
    assert provider.complete_json("sistema", "usuario") == {"valor": 2}
    assert len(completions.kwargs) == 2
    assert completions.kwargs[0]["temperature"] == 0.2
    assert "extra_body" not in completions.kwargs[0]
    assert "response_format" not in completions.kwargs[0]


def test_incomplete_config_disables_ai_without_secrets(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("WARNING")
    provider = build_provider(
        Settings(ai_enabled=True, ai_model="acme/modelo-secreto", openrouter_api_key="")
    )
    assert provider is None
    assert "modelo-secreto" not in caplog.text
    assert "remains disabled" in caplog.text
