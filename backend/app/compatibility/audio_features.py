"""Audio-feature vector compatibility.

Spotify provides per-track audio features (danceability, energy, valence, …)
that we aggregate into a per-user "audio fingerprint". We compare two
fingerprints in two complementary ways:

  1. Cosine similarity on the normalized 0..1 features (scale-invariant)
  2. Per-feature delta -> bell-curved similarity (so we can show "you're
     65% similar on energy" type breakdowns to the UI).

Tempo and loudness are excluded from cosine because their scales are different
(tempo ~ 60-180 BPM, loudness ~ -60..0 dB), but we surface them in deltas.
"""
from __future__ import annotations

import math

import numpy as np

from ..schemas import AudioFeatureBreakdown, AudioFingerprint, TasteProfile

NORMALIZED_FEATURES = (
    "danceability",
    "energy",
    "valence",
    "acousticness",
    "instrumentalness",
    "liveness",
    "speechiness",
)

# tempo & loudness use abs delta with a tolerance band
TEMPO_TOLERANCE = 30.0     # BPM beyond which similarity ~0
LOUDNESS_TOLERANCE = 10.0  # dB beyond which similarity ~0


def _vector(fp: AudioFingerprint) -> np.ndarray:
    return np.array([getattr(fp, k) for k in NORMALIZED_FEATURES], dtype=float)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _delta_similarity(a: float, b: float, scale: float = 1.0) -> float:
    """Map abs delta to similarity in [0,1] via a Gaussian-ish bump."""
    diff = abs(a - b) / scale
    return float(math.exp(-2 * diff * diff))


def compute_audio_features(a: TasteProfile, b: TasteProfile) -> AudioFeatureBreakdown:
    fp_a, fp_b = a.audio_fingerprint, b.audio_fingerprint

    if fp_a.sample_size == 0 or fp_b.sample_size == 0:
        return AudioFeatureBreakdown(
            score=0.0,
            your_vector=fp_a,
            their_vector=fp_b,
            deltas={},
        )

    va, vb = _vector(fp_a), _vector(fp_b)
    cos_sim = _cosine(va, vb)

    # Per-feature similarities for UI (scale 1.0 = full range 0..1)
    deltas: dict[str, float] = {}
    for feat in NORMALIZED_FEATURES:
        deltas[feat] = round(
            _delta_similarity(getattr(fp_a, feat), getattr(fp_b, feat), scale=1.0),
            4,
        )
    deltas["tempo"] = round(
        _delta_similarity(fp_a.tempo, fp_b.tempo, scale=TEMPO_TOLERANCE),
        4,
    )
    deltas["loudness"] = round(
        _delta_similarity(fp_a.loudness, fp_b.loudness, scale=LOUDNESS_TOLERANCE),
        4,
    )

    # Final score: weighted blend of cosine + average per-feature similarity
    avg_delta = float(np.mean(list(deltas.values())))
    blended = 0.6 * max(0.0, cos_sim) + 0.4 * avg_delta
    score = round(blended * 100, 2)

    return AudioFeatureBreakdown(
        score=score,
        your_vector=fp_a,
        their_vector=fp_b,
        deltas=deltas,
    )
