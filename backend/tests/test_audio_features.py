"""Tests for audio-feature-vector compatibility."""
from __future__ import annotations

from app.compatibility.audio_features import compute_audio_features
from app.schemas import AudioFingerprint, TasteProfile, UserPublic


def test_identical_fingerprints(profile_alice):
    result = compute_audio_features(profile_alice, profile_alice)
    assert result.score > 95
    for v in result.deltas.values():
        assert v > 0.95


def test_similar_fingerprints(profile_alice, profile_bob):
    result = compute_audio_features(profile_alice, profile_bob)
    # Alice and Bob have similar audio profiles
    assert result.score > 70


def test_divergent_fingerprints(profile_alice, profile_charlie):
    result = compute_audio_features(profile_alice, profile_charlie)
    # Charlie's audio profile is very different from alice's
    assert result.score < 70
    # instrumentalness diverges most: alice=0.05, charlie=0.7
    assert result.deltas["instrumentalness"] < result.deltas["danceability"]


def test_empty_profile_returns_zero():
    empty = TasteProfile(
        user=UserPublic(user_id="x"),
        audio_fingerprint=AudioFingerprint(),
    )
    other = TasteProfile(
        user=UserPublic(user_id="y"),
        audio_fingerprint=AudioFingerprint(
            danceability=0.5, energy=0.5, sample_size=10,
        ),
    )
    result = compute_audio_features(empty, other)
    assert result.score == 0.0
