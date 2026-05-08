"""Spotify OAuth 2.0 with PKCE.

Flow:
  /auth/login    -> generate state + code_verifier, store in DB, 302 to Spotify
  /auth/callback -> exchange code for tokens, fetch /me, upsert user+tokens
  /auth/refresh  -> use refresh_token to get a new access_token (called internally)
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from ..config import get_settings
from ..db import cursor

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"


# ---------- PKCE helpers ----------

def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:128]


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


# ---------- State persistence ----------

def store_state(state: str, code_verifier: str) -> None:
    with cursor() as c:
        c.execute(
            "INSERT INTO oauth_states (state, code_verifier) VALUES (?, ?)",
            [state, code_verifier],
        )


def consume_state(state: str) -> str | None:
    with cursor() as c:
        row = c.execute(
            "SELECT code_verifier FROM oauth_states WHERE state = ?", [state]
        ).fetchone()
        if row:
            c.execute("DELETE FROM oauth_states WHERE state = ?", [state])
            return row[0]
    return None


# ---------- Authorization URL ----------

def build_authorize_url() -> tuple[str, str]:
    settings = get_settings()
    state = secrets.token_urlsafe(24)
    verifier = _generate_code_verifier()
    challenge = _code_challenge(verifier)
    store_state(state, verifier)

    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": settings.spotify_scopes,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "show_dialog": "false",
    }
    return f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}", state


# ---------- Token exchange & refresh ----------

async def exchange_code(code: str, code_verifier: str) -> dict:
    settings = get_settings()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.spotify_redirect_uri,
        "client_id": settings.spotify_client_id,
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(SPOTIFY_TOKEN_URL, data=data)
        r.raise_for_status()
        return r.json()


async def refresh_access_token(refresh_token: str) -> dict:
    settings = get_settings()
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.spotify_client_id,
    }
    # PKCE clients don't need client_secret, but Spotify accepts both forms.
    auth = None
    if settings.spotify_client_secret:
        auth = (settings.spotify_client_id, settings.spotify_client_secret)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(SPOTIFY_TOKEN_URL, data=data, auth=auth)
        r.raise_for_status()
        return r.json()


async def fetch_spotify_user(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            SPOTIFY_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if r.status_code != 200:
            # Surface Spotify's actual error body to logs / response
            import logging
            logging.getLogger(__name__).error(
                "Spotify /me failed: %s %s", r.status_code, r.text
            )
        r.raise_for_status()
        return r.json()


# ---------- Persistence ----------

def upsert_user(spotify_user: dict) -> str:
    user_id = spotify_user["id"]
    images = spotify_user.get("images") or []
    image_url = images[0]["url"] if images else None
    now = datetime.now(timezone.utc)
    with cursor() as c:
        c.execute(
            """
            INSERT INTO users
                (user_id, display_name, email, image_url, country, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                display_name = excluded.display_name,
                email        = excluded.email,
                image_url    = excluded.image_url,
                country      = excluded.country,
                updated_at   = excluded.updated_at
            """,
            [
                user_id,
                spotify_user.get("display_name"),
                spotify_user.get("email"),
                image_url,
                spotify_user.get("country"),
                now,
            ],
        )
    return user_id


def store_tokens(user_id: str, token_response: dict) -> None:
    expires_in = int(token_response.get("expires_in", 3600))
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in - 30)
    with cursor() as c:
        c.execute(
            """
            INSERT INTO oauth_tokens
                (user_id, access_token, refresh_token, expires_at, scope, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                access_token  = excluded.access_token,
                refresh_token = COALESCE(excluded.refresh_token, oauth_tokens.refresh_token),
                expires_at    = excluded.expires_at,
                scope         = excluded.scope,
                updated_at    = excluded.updated_at
            """,
            [
                user_id,
                token_response["access_token"],
                token_response.get("refresh_token"),
                expires_at,
                token_response.get("scope"),
                now,
            ],
        )


def get_tokens(user_id: str) -> dict | None:
    with cursor() as c:
        row = c.execute(
            """
            SELECT access_token, refresh_token, expires_at, scope
            FROM oauth_tokens WHERE user_id = ?
            """,
            [user_id],
        ).fetchone()
    if not row:
        return None
    return {
        "access_token": row[0],
        "refresh_token": row[1],
        "expires_at": row[2],
        "scope": row[3],
    }


async def get_valid_access_token(user_id: str) -> str:
    """Return a valid (auto-refreshed) access token for the user."""
    tokens = get_tokens(user_id)
    if not tokens:
        raise RuntimeError(f"No tokens for user {user_id}")
    expires_at = tokens["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < expires_at:
        return tokens["access_token"]
    # Expired -> refresh
    refreshed = await refresh_access_token(tokens["refresh_token"])
    # If Spotify omits refresh_token in response, keep the old one
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = tokens["refresh_token"]
    store_tokens(user_id, refreshed)
    return refreshed["access_token"]
