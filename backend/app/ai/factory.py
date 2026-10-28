import logging

from app.ai.base import LLMProvider
from app.ai.openrouter_provider import OpenRouterProvider
from app.core.config import Settings

logger = logging.getLogger("app.ai")


def build_provider(settings: Settings) -> LLMProvider | None:
    if not settings.ai_enabled:
        return None
    if not settings.ai_model or not settings.openrouter_api_key:
        logger.warning(
            "AI_ENABLED is true but AI_MODEL or OPENROUTER_API_KEY is missing; AI remains disabled"
        )
        return None
    return OpenRouterProvider(settings)
