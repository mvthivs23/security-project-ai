import logging
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.ai.factory import build_provider
from app.ai.catalog import load_catalog
from app.api.ai import router as ai_router
from app.api.health import router as health_router
from app.core.config import Settings, get_settings, resolve_dir
from app.core.errors import MSG_GENERIC, MSG_TOO_LONG, error_body
from app.core.security import BodyLimitMiddleware, RateLimiter, SecurityHeadersMiddleware

_AUTO = object()


def create_app(settings: Settings | None = None, provider: Any = _AUTO) -> FastAPI:
    settings = settings or get_settings()
    if provider is _AUTO:
        provider = build_provider(settings)
    app = FastAPI(title="Security Tech AI", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.provider = provider
    app.state.limiter = RateLimiter(settings.ai_rate_limit_per_minute)
    app.state.catalog = load_catalog()
    app.include_router(health_router, prefix="/api")
    app.include_router(ai_router, prefix="/api")
    static_dir = resolve_dir("frontend/static")
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            allow_credentials=False,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: object, exc: RequestValidationError) -> JSONResponse:
        code = "error"
        message = MSG_GENERIC
        for error in exc.errors():
            if error.get("type") == "string_too_long" and "context" in (error.get("loc") or ()):
                code = "prompt_too_large"
                message = MSG_TOO_LONG
                break
        status = 413 if code == "prompt_too_large" else 422
        return JSONResponse(status_code=status, content=error_body(code, message))

    return app


logging.getLogger("app").setLevel(logging.INFO)
app = create_app()
