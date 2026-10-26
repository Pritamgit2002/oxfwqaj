import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

logger = logging.getLogger("windsight.http")


def add_request_context(app: FastAPI) -> None:
    """Tag every response with a request id and its server time, and log one line per request."""

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.1f}"
        logger.info(
            "%s %s %d %.1fms request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response
