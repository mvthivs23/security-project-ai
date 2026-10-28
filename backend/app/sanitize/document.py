import re

from app.sanitize.redact import redact

DOC_MAX_CHARS = 8000

_INJECTION: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(ignor\w*|olvid\w*|omit\w*|disregard|forget|override|sobrescrib\w*|desobedec\w*)\b.{0,50}\b(instrucci\w*|instruction\w*|regla\w*|rules?|prompt|anterior\w*|previous|above|todo lo)",
            re.IGNORECASE | re.ASCII,
        ),
        "Pide ignorar instrucciones",
    ),
    (
        re.compile(
            r"\b(system prompt|prompt (del|de) sistema|mensaje (del|de) sistema|developer mode|modo desarrollador|jailbreak|DAN mode)\b",
            re.IGNORECASE | re.ASCII,
        ),
        "Menciona el prompt o modos del modelo",
    ),
    (
        re.compile(
            r"\b(you are now|ahora eres|a partir de ahora (eres|act[uú]as?|responde\w*)|from now on|pretend to be|finge ser|haz de cuenta que eres|roleplay)\b",
            re.IGNORECASE | re.ASCII,
        ),
        "Intenta cambiar el rol del modelo",
    ),
    (
        re.compile(r"^\s*(system|assistant|user|sistema|asistente|usuario)\s*:", re.IGNORECASE | re.ASCII),
        "Imita un turno de conversación",
    ),
    (
        re.compile(
            r"\b(responde|respond|answer|devuelve|return|output|clasifica|marca|asigna|set)\b.{0,60}\b((nivel|level)\s*)?L[123]\b",
            re.IGNORECASE | re.ASCII,
        ),
        "Intenta fijar el nivel del plan",
    ),
    (
        re.compile(
            r"\b(no (se )?(requiere\w*|necesita\w*)|omite|elimina|quita)\b.{0,15}\b(ning[uú]n )?(control(es)?|guardrails|controles de seguridad)\b",
            re.IGNORECASE | re.ASCII,
        ),
        "Intenta quitar controles",
    ),
    (
        re.compile(
            r"\b(no (menciones|reveles|informes|digas)|do not (mention|reveal|tell))\b.{0,40}\b(estas instrucciones|este mensaje|esto|these instructions|this message|that you)\b",
            re.IGNORECASE | re.ASCII,
        ),
        "Pide ocultar información",
    ),
    (
        re.compile(
            r"\b(env[ií]a|send|exfiltr\w*|reenv[ií]a|forward|filtra|leak)\b.{0,60}\b(prompt|instrucciones|instructions|credencial\w*|credentials?|contraseñ\w*|passwords?|tokens?|secretos?|secrets?|todo el contexto|the context)\b",
            re.IGNORECASE | re.ASCII,
        ),
        "Pide enviar datos o secretos hacia afuera",
    ),
    (
        re.compile(r"\b(base64|rot13|decodifica|decode this|hex[- ]?encoded)\b", re.IGNORECASE | re.ASCII),
        "Contenido codificado",
    ),
    (
        re.compile(
            r"<\|[^|]{0,30}\|>|\[/?INST\]|</?(system|assistant|user|s)>|###\s*(instruction|system)",
            re.IGNORECASE | re.ASCII,
        ),
        "Tokens de control de modelos",
    ),
]

_TAG_CHARS = re.compile("[\U000E0000-\U000E007F]")
_INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\u00ad\u034f\u180e]")
_CONTROLS = re.compile("[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")
_HTML = re.compile(r"</?[a-z][^>]{0,200}>", re.IGNORECASE)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_URL = re.compile(r"\b(?:https?|ftp|file|data|javascript):[^\s)\]>\"']+", re.IGNORECASE)
_WWW = re.compile(r"\bwww\.[^\s)\]>\"']+", re.IGNORECASE)
_DELIMS = re.compile(r"<{2,}|>{2,}|```")
_BLOBS = re.compile(r"\b[A-Za-z0-9+/]{60,}={0,2}")


def _count_sub(pattern: re.Pattern[str], text: str, token: str, counter: dict[str, int], key: str) -> str:
    def repl(_: re.Match[str]) -> str:
        counter[key] += 1
        return token

    return pattern.sub(repl, text)


def sanitize_document(raw: str | None) -> dict[str, object]:
    counts = {"invis": 0, "urls": 0, "html": 0, "blobs": 0, "delims": 0}
    text = _normalize(str(raw or ""))
    text = _count_sub(_TAG_CHARS, text, "", counts, "invis")
    text = _count_sub(_INVISIBLE, text, "", counts, "invis")
    text = _count_sub(_CONTROLS, text, "", counts, "invis")
    removed: list[dict[str, str]] = []
    kept: list[str] = []
    for line in re.split(r"\r?\n", text):
        hit = next((reason for pattern, reason in _INJECTION if pattern.search(line)), None)
        if hit and line.strip():
            removed.append({"t": line.strip()[:220], "why": hit})
        else:
            kept.append(re.sub(r"[ \t]{2,}", " ", line).rstrip())
    text = "\n".join(kept)
    text = _count_sub(_HTML, text, "", counts, "html")
    text = _count_sub(_IMAGE, text, "[IMAGEN]", counts, "urls")
    text = _count_sub(_URL, text, "[ENLACE]", counts, "urls")
    text = _count_sub(_WWW, text, "[ENLACE]", counts, "urls")
    text = _count_sub(_DELIMS, text, "", counts, "delims")
    text = _count_sub(_BLOBS, text, "[BLOQUE CODIFICADO]", counts, "blobs")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    redacted = redact(text)
    text = str(redacted["text"])
    truncated = len(text) > DOC_MAX_CHARS
    if truncated:
        text = re.sub(r"\s+\S*$", "", text[:DOC_MAX_CHARS]) + " …"
    return {"text": text, "removed": removed, "counts": counts, "red": redacted["hits"], "trunc": truncated}


def _normalize(text: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKC", text)
