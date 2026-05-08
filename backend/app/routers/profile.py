"""Profile endpoints: build, fetch, list."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.session import current_user_id
from ..db import cursor
from ..profile.builder import (
    build_taste_profile,
    get_or_build_profile,
    load_profile,
)
from ..schemas import TasteProfile, UserPublic

log = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=TasteProfile)
async def get_my_profile(
    refresh: bool = Query(False, description="Force re-fetch from Spotify"),
    user_id: str = Depends(current_user_id),
) -> TasteProfile:
    return await get_or_build_profile(user_id, force=refresh)


@router.post("/me/refresh", response_model=TasteProfile)
async def refresh_my_profile(user_id: str = Depends(current_user_id)) -> TasteProfile:
    return await build_taste_profile(user_id)


@router.get("/{target_user_id}", response_model=TasteProfile)
async def get_profile(target_user_id: str) -> TasteProfile:
    profile = load_profile(target_user_id)
    if not profile:
        raise HTTPException(404, f"No profile for {target_user_id}")
    return profile


@router.get("", response_model=list[UserPublic])
async def list_users() -> list[UserPublic]:
    """List all users who have built profiles (for the demo UI to pick a match)."""
    with cursor() as c:
        rows = c.execute(
            """
            SELECT u.user_id, u.display_name, u.image_url, u.country
            FROM users u
            JOIN taste_profiles t ON t.user_id = u.user_id
            ORDER BY t.built_at DESC
            """
        ).fetchall()
    return [
        UserPublic(user_id=r[0], display_name=r[1], image_url=r[2], country=r[3])
        for r in rows
    ]
