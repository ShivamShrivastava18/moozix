"""Auth endpoints: Spotify OAuth login + callback + logout + status."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from ..auth import session as session_mod
from ..auth.spotify_oauth import (
    build_authorize_url,
    consume_state,
    exchange_code,
    fetch_spotify_user,
    store_tokens,
    upsert_user,
)
from ..config import get_settings
from ..db import cursor

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login() -> RedirectResponse:
    """Redirect the browser to Spotify's authorize URL."""
    url, _state = build_authorize_url()
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None,
                   error: str | None = None) -> RedirectResponse:
    """Spotify redirects here after user grants/denies access."""
    settings = get_settings()
    if error:
        log.warning("Spotify auth error: %s", error)
        return RedirectResponse(f"{settings.frontend_url}/?error={error}")
    if not code or not state:
        raise HTTPException(400, "Missing code or state")

    verifier = consume_state(state)
    if not verifier:
        raise HTTPException(400, "Invalid or expired state")

    token_response = await exchange_code(code, verifier)
    spotify_user = await fetch_spotify_user(token_response["access_token"])
    user_id = upsert_user(spotify_user)
    store_tokens(user_id, token_response)

    session_token = session_mod.encode_session(user_id)
    redirect = RedirectResponse(f"{settings.frontend_url}/post-login")
    redirect.set_cookie(value=session_token, **session_mod.cookie_kwargs())
    return redirect


@router.post("/logout")
async def logout() -> dict:
    response = {"ok": True}
    # Cookie clear handled at the response level by the caller
    return response


@router.get("/status")
async def status_endpoint(request: Request) -> dict:
    uid = session_mod.optional_user_id(request)
    if not uid:
        return {"authenticated": False}
    with cursor() as c:
        row = c.execute(
            "SELECT user_id, display_name, image_url FROM users WHERE user_id = ?",
            [uid],
        ).fetchone()
    if not row:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {"user_id": row[0], "display_name": row[1], "image_url": row[2]},
    }
