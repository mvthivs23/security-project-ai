from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
BODY_LIMIT_BYTES = 64 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ai_enabled: bool = False
    ai_model: str = ""
    openrouter_api_key: str = ""
    ai_timeout_seconds: float = 60
    ai_max_output_tokens: int = 4000
    ai_temperature: float | None = None
    ai_json_mode: bool = False
    openrouter_zdr: bool = True
    openrouter_app_title: str = ""
    ai_rate_limit_per_minute: int = Field(default=10, ge=1)
    allowed_origins: str = ""

    @field_validator("ai_temperature", mode="before")
    @classmethod
    def empty_temperature(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @field_validator("ai_model", "openrouter_api_key", "openrouter_app_title", mode="before")
    @classmethod
    def empty_text(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_enabled and self.ai_model and self.openrouter_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_dir(name: str) -> Path:
    cwd_candidate = Path.cwd() / name
    if cwd_candidate.exists():
        return cwd_candidate
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / name
        if candidate.exists():
            return candidate
    return cwd_candidate
