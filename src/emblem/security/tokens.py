"""Minimal HS256 bearer tokens (sub, role, exp). Secret from env; constant-time verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class TokenError(Exception):
    pass


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue(secret: bytes, sub: str, role: str, ttl: int = 3600, now: float | None = None) -> str:
    body = _b64(json.dumps({"sub": sub, "role": role, "exp": int((now or time.time()) + ttl)}).encode())
    return f"{body}.{_b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())}"


def verify(secret: bytes, token: str, now: float | None = None) -> dict[str, Any]:
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise TokenError("bad signature")
        claims: dict[str, Any] = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise TokenError("malformed token") from exc
    if claims["exp"] < (now or time.time()):
        raise TokenError("token expired")
    return claims
