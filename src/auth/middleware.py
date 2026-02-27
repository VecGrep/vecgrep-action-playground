"""Authentication middleware for request pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .authentication import Session, validate_token


@dataclass
class Request:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes = b""


@dataclass
class Response:
    status: int
    body: str
    headers: dict[str, str] | None = None


Handler = Callable[[Request, Session], Response]


def auth_middleware(handler: Handler) -> Callable[[Request], Response]:
    """
    Wrap a handler with token-based authentication.
    Extracts Bearer token from Authorization header, validates it,
    and passes the Session to the inner handler.
    """
    def wrapped(request: Request) -> Response:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(status=401, body="Unauthorized: missing or malformed token.")

        token = auth_header.removeprefix("Bearer ").strip()
        session = validate_token(token)
        if not session:
            return Response(status=401, body="Unauthorized: invalid or expired token.")

        return handler(request, session)

    return wrapped


def rate_limit_middleware(
    handler: Callable[[Request], Response],
    max_requests: int = 100,
    window_seconds: int = 60,
) -> Callable[[Request], Response]:
    """
    Simple in-memory rate limiter keyed by client IP.
    Rejects requests that exceed max_requests per window_seconds.
    """
    import time
    _counts: dict[str, list[float]] = {}

    def wrapped(request: Request) -> Response:
        client_ip = request.headers.get("X-Forwarded-For", "unknown")
        now = time.time()
        window_start = now - window_seconds
        timestamps = [t for t in _counts.get(client_ip, []) if t > window_start]
        timestamps.append(now)
        _counts[client_ip] = timestamps

        if len(timestamps) > max_requests:
            return Response(status=429, body="Too Many Requests.")

        return handler(request)

    return wrapped
