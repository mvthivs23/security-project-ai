import re

_FLAGS = re.ASCII

RED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b", _FLAGS), "[RUT]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", _FLAGS), "[CORREO]"),
    (re.compile(r"(\+?56\s?)?9\s?\d{4}\s?\d{4}\b", _FLAGS), "[TELÉFONO]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", _FLAGS), "[IP]"),
    (
        re.compile(
            r"\b(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|xox[bpa]-[A-Za-z0-9-]{10,}|[A-Za-z0-9+/_-]{32,})\b",
            _FLAGS,
        ),
        "[SECRETO]",
    ),
]


def redact(value: str | None) -> dict[str, object]:
    text = re.sub(r"<<<|>>>", "", str(value or ""))
    hits: list[str] = []
    for pattern, token in RED:
        found = pattern.findall(text)
        if found:
            hits.append(f"{token} ×{len(found)}")
            text = pattern.sub(token, text)
    return {"text": text, "hits": hits}
