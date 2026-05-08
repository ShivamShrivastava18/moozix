"""Cookie-based session management using itsdangerous signed tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer

from ..config import get_settings

SESSION_COOKIE_NAME = "moozix_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="moozix.session")


def encode_session(user_id: str) -> str:
    return _serializer().dumps({"uid": user_id, "iat": datetime.now(timezone.utc).isoformat()})


def decode_session(token: str) -> str | None:
    try:
        data = _serializer().loads(token, max_age=SESSION_TTL_SECONDS)
        return data.get("uid")
    except BadSignature:
        return None


def current_user_id(request: Request) -> str:
    """FastAPI dependency: require an authenticated user."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    uid = decode_session(token)
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    return uid


def optional_user_id(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return decode_session(token)


def cookie_kwargs() -> dict:
    return {
        "key": SESSION_COOKIE_NAME,
        "max_age": SESSION_TTL_SECONDS,
        "httponly": True,
        "samesite": "lax",
        "secure": False,  # set True in prod with HTTPS
        "path": "/",
    }
