"""Async Spotify Web API client.

Handles:
  - bearer auth + auto refresh via auth.spotify_oauth.get_valid_access_token
  - retries on 429 (rate limit) and 5xx
  - batched endpoints for tracks/artists/audio-features
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..auth.spotify_oauth import get_valid_access_token

log = logging.getLogger(__name__)

API_BASE = "https://api.spotify.com/v1"


class SpotifyAPIError(Exception):
    pass


class SpotifyClient:
    """Async client scoped to a single user (uses their access token)."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._client = httpx.AsyncClient(timeout=20)

    async def __aenter__(self) -> "SpotifyClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    # ---------- Core ----------

    async def _headers(self) -> dict[str, str]:
        token = await get_valid_access_token(self.user_id)
        return {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{API_BASE}{path}" if path.startswith("/") else path
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TransportError, SpotifyAPIError)),
            reraise=True,
        ):
            with attempt:
                headers = await self._headers()
                kwargs.setdefault("headers", {}).update(headers)
                r = await self._client.request(method, url, **kwargs)
                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", "1"))
                    log.warning("Rate limited, sleeping %ss", retry_after)
                    await asyncio.sleep(retry_after)
                    raise SpotifyAPIError("rate-limited, retrying")
                if r.status_code == 401:
                    raise SpotifyAPIError("unauthorized")
                if r.status_code >= 500:
                    raise SpotifyAPIError(f"server error {r.status_code}")
                if r.status_code == 204:
                    return None
                if not r.is_success:
                    raise SpotifyAPIError(f"{r.status_code}: {r.text[:200]}")
                return r.json()

    async def get(self, path: str, **params) -> Any:
        return await self._request("GET", path, params=params or None)

    # ---------- High-level endpoints ----------

    async def me(self) -> dict:
        return await self.get("/me")

    async def top_artists(self, time_range: str = "medium_term", limit: int = 50) -> list[dict]:
        data = await self.get("/me/top/artists", time_range=time_range, limit=limit)
        return (data or {}).get("items", [])

    async def top_tracks(self, time_range: str = "medium_term", limit: int = 50) -> list[dict]:
        data = await self.get("/me/top/tracks", time_range=time_range, limit=limit)
        return (data or {}).get("items", [])

    async def saved_tracks(self, limit: int = 50, offset: int = 0) -> list[dict]:
        data = await self.get("/me/tracks", limit=limit, offset=offset)
        return (data or {}).get("items", [])

    async def all_saved_tracks(self, max_items: int = 500) -> list[dict]:
        items: list[dict] = []
        offset = 0
        while len(items) < max_items:
            page = await self.saved_tracks(limit=50, offset=offset)
            if not page:
                break
            items.extend(page)
            if len(page) < 50:
                break
            offset += 50
        return items[:max_items]

    async def recently_played(self, limit: int = 50) -> list[dict]:
        data = await self.get("/me/player/recently-played", limit=limit)
        return (data or {}).get("items", [])

    async def audio_features_batch(self, track_ids: list[str]) -> list[dict]:
        """Fetch audio features for up to 100 track ids per call."""
        results: list[dict] = []
        for i in range(0, len(track_ids), 100):
            chunk = [tid for tid in track_ids[i : i + 100] if tid]
            if not chunk:
                continue
            data = await self.get("/audio-features", ids=",".join(chunk))
            features = (data or {}).get("audio_features") or []
            results.extend([f for f in features if f])
        return results

    async def artists_batch(self, artist_ids: list[str]) -> list[dict]:
        """Fetch artist info for up to 50 artist ids per call."""
        results: list[dict] = []
        for i in range(0, len(artist_ids), 50):
            chunk = [aid for aid in artist_ids[i : i + 50] if aid]
            if not chunk:
                continue
            data = await self.get("/artists", ids=",".join(chunk))
            results.extend((data or {}).get("artists") or [])
        return results
