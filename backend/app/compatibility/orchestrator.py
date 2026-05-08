"""Orchestrate the four compatibility scorers and combine into a final result."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ..db import cursor, from_json, to_json
from ..schemas import (
    CompatibilityResult,
    TasteProfile,
)
from .audio_features import compute_audio_features
from .embeddings import compute_embedding
from .llm_report import compute_llm_report
from .overlap import compute_overlap

log = logging.getLogger(__name__)


# Default weights for the final score. Overlap weighs most because it's the
# highest-fidelity signal (concrete shared items); LLM is excluded from the
# numeric score because it's qualitative.
DEFAULT_WEIGHTS = {
    "overlap": 0.45,
    "embedding": 0.30,
    "audio_features": 0.25,
}


def _pair_key(user_a: str, user_b: str) -> tuple[str, str]:
    return tuple(sorted([user_a, user_b]))  # type: ignore[return-value]


def get_cached_comparison(user_a: str, user_b: str) -> CompatibilityResult | None:
    a, b = _pair_key(user_a, user_b)
    with cursor() as c:
        row = c.execute(
            "SELECT result_json FROM comparisons WHERE user_a = ? AND user_b = ?",
            [a, b],
        ).fetchone()
    if not row:
        return None
    return CompatibilityResult.model_validate_json(row[0])


def save_comparison(result: CompatibilityResult) -> None:
    a, b = _pair_key(result.user_a.user_id, result.user_b.user_id)
    with cursor() as c:
        c.execute(
            """
            INSERT INTO comparisons (user_a, user_b, result_json, computed_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_a, user_b) DO UPDATE SET
                result_json = excluded.result_json,
                computed_at = CURRENT_TIMESTAMP
            """,
            [a, b, result.model_dump_json()],
        )


async def compute_compatibility(
    profile_a: TasteProfile,
    profile_b: TasteProfile,
    weights: dict[str, float] | None = None,
    include_llm: bool = True,
) -> CompatibilityResult:
    """Run all scorers (concurrently where useful) and combine."""
    weights = weights or DEFAULT_WEIGHTS

    # Sync scorers can run via asyncio.to_thread to avoid blocking event loop
    overlap_task = asyncio.to_thread(compute_overlap, profile_a, profile_b)
    embedding_task = asyncio.to_thread(compute_embedding, profile_a, profile_b)
    audio_task = asyncio.to_thread(compute_audio_features, profile_a, profile_b)

    overlap, embedding, audio = await asyncio.gather(
        overlap_task, embedding_task, audio_task
    )

    # LLM runs after we have the other scores so it can reference them
    llm = None
    if include_llm:
        llm = await compute_llm_report(profile_a, profile_b, overlap, embedding, audio)

    overall = (
        weights["overlap"] * overlap.score
        + weights["embedding"] * embedding.score
        + weights["audio_features"] * audio.score
    )
    overall = round(min(100.0, max(0.0, overall)), 2)

    breakdown_summary = {
        "overlap": overlap.score,
        "embedding": embedding.score,
        "audio_features": audio.score,
        "weights": weights,
    }

    result = CompatibilityResult(
        user_a=profile_a.user,
        user_b=profile_b.user,
        overall_score=overall,
        breakdown=breakdown_summary,
        overlap=overlap,
        embedding=embedding,
        audio_features=audio,
        llm=llm,
        generated_at=datetime.now(timezone.utc),
    )
    save_comparison(result)
    return result
