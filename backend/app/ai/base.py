from typing import Protocol


class ProviderError(Exception):
    pass


class InvalidJsonError(ProviderError):
    pass


class LLMProvider(Protocol):
    def complete_json(self, system: str, user: str) -> dict: ...


class FakeProvider:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = {} if payload is None else payload
        self.error = error
        self.calls: list[dict[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append({"system": system, "user": user})
        if self.error is not None:
            raise self.error
        return self.payload
