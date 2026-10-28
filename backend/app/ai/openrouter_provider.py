from openai import OpenAI

from app.ai.base import InvalidJsonError, ProviderError
from app.ai.jsonutil import extract_json_object
from app.core.config import OPENROUTER_BASE_URL, Settings


class OpenRouterProvider:
    def __init__(self, settings: Settings, client: object | None = None) -> None:
        self._settings = settings
        if client is not None:
            self._client = client
            return
        kwargs: dict = {
            "base_url": OPENROUTER_BASE_URL,
            "api_key": settings.openrouter_api_key,
            "timeout": settings.ai_timeout_seconds,
            "max_retries": 0,
        }
        title = settings.openrouter_app_title.strip()
        if title:
            kwargs["default_headers"] = {"X-OpenRouter-Title": title}
        self._client = OpenAI(**kwargs)

    def complete_json(self, system: str, user: str) -> dict:
        for _attempt in range(2):
            parsed = extract_json_object(self._complete(system, user))
            if isinstance(parsed, dict):
                return parsed
        raise InvalidJsonError()

    def _complete(self, system: str, user: str) -> str:
        settings = self._settings
        kwargs: dict = {
            "model": settings.ai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": settings.ai_max_output_tokens,
        }
        if settings.ai_temperature is not None:
            kwargs["temperature"] = settings.ai_temperature
        if settings.ai_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if settings.openrouter_zdr:
            kwargs["extra_body"] = {"provider": {"zdr": True}}
        try:
            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(type(exc).__name__) from None
