from fastapi.testclient import TestClient

from app.ai.base import FakeProvider
from app.core.config import Settings
from app.main import create_app


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "ai_enabled": False,
        "ai_model": "",
        "openrouter_api_key": "",
        "ai_temperature": None,
        "ai_json_mode": False,
        "openrouter_zdr": True,
        "openrouter_app_title": "",
        "ai_rate_limit_per_minute": 10,
        "allowed_origins": "",
        "ai_timeout_seconds": 60,
        "ai_max_output_tokens": 4000,
    }
    values.update(overrides)
    return Settings(**values)


def make_client(provider: FakeProvider | None = None, **overrides: object) -> TestClient:
    if provider is not None:
        overrides.setdefault("ai_enabled", True)
        overrides.setdefault("ai_model", "synthetic/test-model")
        overrides.setdefault("openrouter_api_key", "sk-test-not-real")
    return TestClient(create_app(settings(**overrides), provider))
