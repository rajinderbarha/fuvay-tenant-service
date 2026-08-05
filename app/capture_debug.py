"""TEMPORARY diagnostic capture — safe to delete.

Records real request/response pairs to a JSONL file so a failing screen can
be diagnosed from what the server ACTUALLY sent, rather than from a guess.

Disabled unless `SERVICEOS_CAPTURE_FILE` is set, so it costs nothing and
changes nothing in a normal run. It never alters a response: the body is
read from the outgoing stream and re-emitted byte-for-byte.
"""
from __future__ import annotations

import json
import os
import time
import traceback

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

#: Only capture what we are actually debugging -- capturing everything
#: would bury the interesting request in noise.
CAPTURED_PREFIXES = ("/v1/",)  # widened: capture every API call

MAX_BODY_CHARS = 20000


def _record(path: str, payload: dict) -> None:
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:  # pragma: no cover - diagnostics must never break a request
        pass


class CaptureDebugMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, capture_path: str):
        super().__init__(app)
        self.capture_path = capture_path

    async def dispatch(self, request, call_next):
        interesting = request.url.path.startswith(CAPTURED_PREFIXES)
        if not interesting:
            return await call_next(request)

        started = time.time()
        try:
            response = await call_next(request)
        except Exception as exc:
            _record(self.capture_path, {
                "ts": time.time(),
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status": "EXCEPTION",
                "error": repr(exc),
                "traceback": traceback.format_exc()[-4000:],
            })
            raise

        # Drain the body so it can be logged, then hand back an identical
        # response -- the original iterator is consumed by this read.
        chunks = [chunk async for chunk in response.body_iterator]
        body = b"".join(chunks)

        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            text = f"<{len(body)} non-utf8 bytes>"

        _record(self.capture_path, {
            "ts": time.time(),
            "ms": round((time.time() - started) * 1000, 1),
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
            "status": response.status_code,
            "body": text[:MAX_BODY_CHARS],
            "truncated": len(text) > MAX_BODY_CHARS,
        })

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


def install_capture(app) -> str | None:
    """Attach the capture middleware if a capture file was configured."""
    path = os.environ.get("SERVICEOS_CAPTURE_FILE")
    if not path:
        return None
    app.add_middleware(CaptureDebugMiddleware, capture_path=path)
    return path
