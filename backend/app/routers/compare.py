"""Compatibility comparison endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth.session import current_user_id
from ..compatibility.orchestrator import (
    compute_compatibility,
    get_cached_comparison,
)
from ..profile.builder import get_or_build_profile, load_profile
from ..schemas import CompatibilityResult

log = logging.getLogger(__name__)
router = APIRouter(prefix="/compare", tags=["compare"])


class CompareRequest(BaseModel):
    user_a: str | None = None  # if omitted, defaults to current authenticated user
    user_b: str
    include_llm: bool = True
    force: bool = False


@router.post("", response_model=CompatibilityResult)
async def compare(
    body: CompareRequest,
    me: str = Depends(current_user_id),
) -> CompatibilityResult:
    user_a = body.user_a or me
    user_b = body.user_b
    if user_a == user_b:
        raise HTTPException(400, "Cannot compare a user with themselves")

    if not body.force:
        cached = get_cached_comparison(user_a, user_b)
        if cached:
            return cached

    # Build/load profiles
    profile_a = (
        await get_or_build_profile(user_a)
        if user_a == me
        else load_profile(user_a)
    )
    profile_b = (
        await get_or_build_profile(user_b)
        if user_b == me
        else load_profile(user_b)
    )
    if profile_a is None:
        raise HTTPException(404, f"No profile for {user_a}")
    if profile_b is None:
        raise HTTPException(404, f"No profile for {user_b}")

    return await compute_compatibility(
        profile_a, profile_b, include_llm=body.include_llm
    )


@router.get("/{user_a}/{user_b}", response_model=CompatibilityResult)
async def get_comparison(user_a: str, user_b: str) -> CompatibilityResult:
    cached = get_cached_comparison(user_a, user_b)
    if not cached:
        raise HTTPException(404, "No cached comparison")
    return cached
