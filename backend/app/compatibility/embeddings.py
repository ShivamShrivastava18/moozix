"""Embedding-based similarity using sentence-transformers.

We render a textual "taste card" for each user (top artists, top tracks, top
genres) and compare embeddings via cosine similarity. The model is loaded
lazily and cached at module level.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from ..config import get_settings
from ..schemas import EmbeddingBreakdown, TasteProfile

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _model():
    # Imported lazily so that startup doesn't pay model-load cost when not needed.
    from sentence_transformers import SentenceTransformer

    name = get_settings().embedding_model
    log.info("Loading sentence-transformers model %s", name)
    return SentenceTransformer(name)


def render_taste_card(profile: TasteProfile) -> str:
    """Build a deterministic, semantically-rich text rendering of the profile."""
    parts: list[str] = []
    artists = (
        list(profile.top_artists_medium)
        or list(profile.top_artists_short)
        or list(profile.top_artists_long)
    )[:25]
    if artists:
        parts.append("Top artists: " + ", ".join(a.name for a in artists if a.name))
    tracks = (
        list(profile.top_tracks_medium)
        or list(profile.top_tracks_short)
        or list(profile.top_tracks_long)
    )[:25]
    if tracks:
        parts.append(
            "Top tracks: "
            + ", ".join(
                f"{t.name} by {', '.join(t.artist_names) or 'unknown'}"
                for t in tracks if t.name
            )
        )
    if profile.genres:
        top_genres = sorted(profile.genres.items(), key=lambda kv: -kv[1])[:20]
        parts.append("Genres: " + ", ".join(g for g, _ in top_genres))
    fp = profile.audio_fingerprint
    parts.append(
        f"Audio mood: energy={fp.energy:.2f}, valence={fp.valence:.2f}, "
        f"danceability={fp.danceability:.2f}, acousticness={fp.acousticness:.2f}"
    )
    return ". ".join(parts)


def compute_embedding(a: TasteProfile, b: TasteProfile) -> EmbeddingBreakdown:
    text_a = render_taste_card(a)
    text_b = render_taste_card(b)
    if not text_a.strip() or not text_b.strip():
        return EmbeddingBreakdown(score=0.0, similarity=0.0)

    model = _model()
    vecs = model.encode([text_a, text_b], normalize_embeddings=True)
    sim = float(np.dot(vecs[0], vecs[1]))
    # Map cosine [-1, 1] -> [0, 100], clipping to [0, 1] since real-world
    # values almost never go negative for this kind of text.
    score = round(max(0.0, sim) * 100, 2)
    return EmbeddingBreakdown(score=score, similarity=round(sim, 4))
