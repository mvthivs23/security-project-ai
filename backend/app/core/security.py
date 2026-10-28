import time
from collections import defaultdict
from threading import Lock

import anyio

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import BODY_LIMIT_BYTES
from app.core.errors import MSG_TOO_LONG, error_body

CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src 'self' data: blob:; "
    "connect-src 'self'; "
    "worker-src 'self' blob:"
)

_SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"content-security-policy", CSP.encode()),
)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                present = {name.lower() for name, _ in headers}
                for name, value in _SECURITY_HEADERS:
                    if name not in present:
                        headers.append((name, value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = BODY_LIMIT_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {name.lower(): value for name, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length:
            try:
                if int(raw_length) > self.max_bytes:
                    await _reject_too_large(send)
                    return
            except ValueError:
                pass
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                await _reject_too_large(send)
                return
            if not message.get("more_body", False):
                break
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            # A real server blocks here until the client goes away. Returning
            # disconnect immediately cancels FileResponse before it sends the file.
            await anyio.sleep_forever()
            return {"type": "http.disconnect"}

        await self.app(scope, replay, send)


async def _reject_too_large(send: Send) -> None:
    response = JSONResponse(status_code=413, content=error_body("prompt_too_large", MSG_TOO_LONG))
    await response({"type": "http"}, _empty_receive, send)


async def _empty_receive() -> Message:
    return {"type": "http.disconnect"}


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            recent = [stamp for stamp in self._hits[key] if now - stamp < self.window_seconds]
            if len(recent) >= self.limit:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True
