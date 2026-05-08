"""LLM-generated narrative compatibility report.

Uses Anthropic's Claude to write a 3-5 sentence narrative explaining the
compatibility, plus structured "vibes" and "clashes" lists for the UI.

Falls back gracefully (returns None / heuristic narrative) if no API key is
configured.
"""
from __future__ import annotations

import json
import logging

from ..config import get_settings
from ..schemas import (
    AudioFeatureBreakdown,
    EmbeddingBreakdown,
    LLMBreakdown,
    OverlapBreakdown,
    TasteProfile,
)

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a witty, thoughtful music critic writing compatibility \
reports between two Spotify users. Your tone is warm, specific, and never generic. \
Reference real artists, tracks, and genres from the data. Avoid clichés. \

Always respond in valid JSON with this exact shape:
{
  "title": "<a short, catchy 3-6 word title for the pairing>",
  "narrative": "<3-5 sentences explaining their musical compatibility>",
  "vibes": ["<3-5 short phrases describing what they share>"],
  "clashes": ["<2-4 short phrases describing where their tastes diverge>"]
}
Output ONLY the JSON, no markdown fences."""


def _profile_summary(profile: TasteProfile, label: str) -> str:
    artists = (profile.top_artists_medium or profile.top_artists_short)[:15]
    tracks = (profile.top_tracks_medium or profile.top_tracks_short)[:10]
    top_genres = sorted(profile.genres.items(), key=lambda kv: -kv[1])[:10]
    fp = profile.audio_fingerprint
    return (
        f"{label} ({profile.user.display_name or profile.user.user_id}):\n"
        f"  Top artists: {', '.join(a.name for a in artists) or 'n/a'}\n"
        f"  Top tracks: "
        + (
            ", ".join(
                f"{t.name} - {', '.join(t.artist_names) or 'unknown'}"
                for t in tracks
            )
            or "n/a"
        )
        + "\n"
        f"  Top genres: {', '.join(g for g, _ in top_genres) or 'n/a'}\n"
        f"  Audio mood: energy={fp.energy:.2f}, valence={fp.valence:.2f}, "
        f"dance={fp.danceability:.2f}, acoustic={fp.acousticness:.2f}\n"
    )


def _fallback(
    overlap: OverlapBreakdown,
    embedding: EmbeddingBreakdown,
    audio: AudioFeatureBreakdown,
) -> LLMBreakdown:
    shared = ", ".join(a.name for a in overlap.shared_artists[:5]) or "no shared headliners"
    genres = ", ".join(overlap.shared_genres[:4]) or "different genre lanes"
    narrative = (
        f"You and your match share {shared}. "
        f"Genre overlap is centered on {genres}. "
        f"Your audio moods land at {audio.score:.0f}/100 similarity, "
        f"and your overall taste embedding aligns at {embedding.score:.0f}/100."
    )
    return LLMBreakdown(
        title="Music Compatibility",
        narrative=narrative,
        vibes=overlap.shared_genres[:5],
        clashes=[],
    )


async def compute_llm_report(
    a: TasteProfile,
    b: TasteProfile,
    overlap: OverlapBreakdown,
    embedding: EmbeddingBreakdown,
    audio: AudioFeatureBreakdown,
) -> LLMBreakdown:
    settings = get_settings()
    if not settings.anthropic_api_key:
        log.info("No Anthropic key set; returning heuristic report")
        return _fallback(overlap, embedding, audio)

    try:
        # Imported lazily so missing key doesn't break startup
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        prompt = (
            _profile_summary(a, "User A")
            + "\n"
            + _profile_summary(b, "User B")
            + "\n\nQuantitative scores (0-100):\n"
            f"  - Direct overlap: {overlap.score}\n"
            f"  - Embedding similarity: {embedding.score}\n"
            f"  - Audio fingerprint: {audio.score}\n"
            f"\nShared artists: {', '.join(x.name for x in overlap.shared_artists[:10]) or 'none'}\n"
            f"Shared genres: {', '.join(overlap.shared_genres[:8]) or 'none'}\n"
        )

        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        ).strip()

        # Strip accidental code fences
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]

        data = json.loads(text)
        return LLMBreakdown(
            title=data.get("title"),
            narrative=data.get("narrative", ""),
            vibes=data.get("vibes", []) or [],
            clashes=data.get("clashes", []) or [],
        )
    except Exception as e:
        log.warning("LLM report failed (%s); falling back", e)
        return _fallback(overlap, embedding, audio)
