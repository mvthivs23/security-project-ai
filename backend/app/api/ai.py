import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.ai.base import InvalidJsonError, ProviderError
from app.ai.profile import AnswersRejected, ensure_answers
from app.ai.prompts.analyze import build_analyze_prompt
from app.ai.prompts.understand import SYSTEM_PROMPT, build_understand_prompt
from app.ai.validators import ai_validate, und_validate
from app.core.errors import (
    MSG_EMPTY_CONTEXT,
    MSG_GENERIC,
    MSG_INVALID_JSON,
    MSG_RATE_ANALYZE,
    MSG_RATE_UNDERSTAND,
    error_body,
)
from app.sanitize.document import sanitize_document
from app.schemas.ai import AnalyzeRequest, UnderstandRequest

logger = logging.getLogger("app.ai")
router = APIRouter(prefix="/ai")


@router.get("/status")
def ai_status(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    if request.app.state.provider is None:
        return {"enabled": False, "provider": None, "model": None}
    return {"enabled": True, "provider": "openrouter", "model": settings.ai_model}


@router.post("/understand")
def understand(body: UnderstandRequest, request: Request) -> JSONResponse:
    limited = _limit(request, MSG_RATE_UNDERSTAND)
    if limited is not None:
        return limited
    if request.app.state.provider is None:
        return _unavailable()
    if not body.context.strip():
        return JSONResponse(status_code=422, content=error_body("error", MSG_EMPTY_CONTEXT))
    rejected = _reject_answers(request, body.answers)
    if rejected is not None:
        return rejected
    sanitized = str(sanitize_document(body.context)["text"])
    prompt = build_understand_prompt(body.answers, sanitized, request.app.state.catalog)
    try:
        raw = _complete(request, "understand", prompt)
    except InvalidJsonError:
        return JSONResponse(status_code=502, content=error_body("invalid_json", MSG_INVALID_JSON))
    except ProviderError:
        return JSONResponse(status_code=502, content=error_body("error", MSG_GENERIC))
    result = und_validate(raw, sanitized, body.answers, request.app.state.catalog)
    result["src"] = body.context
    return JSONResponse(result)


@router.post("/analyze")
def analyze(body: AnalyzeRequest, request: Request) -> JSONResponse:
    limited = _limit(request, MSG_RATE_ANALYZE)
    if limited is not None:
        return limited
    if request.app.state.provider is None:
        return _unavailable()
    rejected = _reject_answers(request, body.answers)
    if rejected is not None:
        return rejected
    sanitized = str(sanitize_document(body.context)["text"])
    prompt = build_analyze_prompt(
        body.answers,
        sanitized,
        body.structured_context,
        body.base_control_ids,
        request.app.state.catalog,
    )
    try:
        raw = _complete(request, "analyze", prompt)
    except InvalidJsonError:
        return JSONResponse(status_code=502, content=error_body("invalid_json", MSG_INVALID_JSON))
    except ProviderError:
        return JSONResponse(status_code=502, content=error_body("error", MSG_GENERIC))
    result = ai_validate(raw, body.answers, request.app.state.catalog, body.base_control_ids)
    result["v"] = 2
    result["at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return JSONResponse(result)


def _limit(request: Request, message: str) -> JSONResponse | None:
    host = request.client.host if request.client else "unknown"
    if request.app.state.limiter.allow(host):
        return None
    return JSONResponse(status_code=429, content=error_body("rate_limited", message))


def _unavailable() -> JSONResponse:
    return JSONResponse(status_code=503, content=error_body("unavailable", MSG_GENERIC))


def _reject_answers(request: Request, answers: object) -> JSONResponse | None:
    try:
        ensure_answers(request.app.state.catalog, answers)
    except AnswersRejected:
        return JSONResponse(status_code=422, content=error_body("error", MSG_GENERIC))
    return None


def _complete(request: Request, operation: str, user_prompt: str) -> dict:
    settings = request.app.state.settings
    started = time.perf_counter()
    result = "error"
    try:
        payload = request.app.state.provider.complete_json(SYSTEM_PROMPT, user_prompt)
        result = "ok"
        return payload
    except InvalidJsonError:
        result = "invalid_json"
        raise
    except ProviderError:
        result = "error"
        raise
    finally:
        logger.info(
            "ai_call provider=%s model=%s operation=%s duration_ms=%d result=%s",
            "openrouter",
            settings.ai_model,
            operation,
            int((time.perf_counter() - started) * 1000),
            result,
        )
