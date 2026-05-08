"""Shared Pydantic response models exposed to the frontend."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------- User / Profile ----------

class UserPublic(BaseModel):
    user_id: str
    display_name: str | None = None
    image_url: str | None = None
    country: str | None = None


class TopArtist(BaseModel):
    id: str
    name: str
    genres: list[str] = []
    popularity: int | None = None
    image_url: str | None = None


class TopTrack(BaseModel):
    uri: str
    id: str
    name: str
    artist_names: list[str] = []
    artist_ids: list[str] = []
    popularity: int | None = None


class AudioFingerprint(BaseModel):
    """Aggregated audio-feature vector for a user (mean across top tracks)."""
    danceability: float = 0.0
    energy: float = 0.0
    valence: float = 0.0
    acousticness: float = 0.0
    instrumentalness: float = 0.0
    liveness: float = 0.0
    speechiness: float = 0.0
    tempo: float = 0.0
    loudness: float = 0.0
    sample_size: int = 0


class TasteProfile(BaseModel):
    user: UserPublic
    top_artists_short: list[TopArtist] = []
    top_artists_medium: list[TopArtist] = []
    top_artists_long: list[TopArtist] = []
    top_tracks_short: list[TopTrack] = []
    top_tracks_medium: list[TopTrack] = []
    top_tracks_long: list[TopTrack] = []
    genres: dict[str, float] = Field(
        default_factory=dict,
        description="Genre → weight (normalized 0..1)",
    )
    audio_fingerprint: AudioFingerprint = Field(default_factory=AudioFingerprint)
    built_at: datetime | None = None


# ---------- Compatibility ----------

class OverlapBreakdown(BaseModel):
    score: float
    artist_jaccard: float
    track_jaccard: float
    genre_cosine: float
    shared_artists: list[TopArtist] = []
    shared_tracks: list[TopTrack] = []
    shared_genres: list[str] = []


class EmbeddingBreakdown(BaseModel):
    score: float
    similarity: float


class AudioFeatureBreakdown(BaseModel):
    score: float
    your_vector: AudioFingerprint
    their_vector: AudioFingerprint
    deltas: dict[str, float] = {}


class LLMBreakdown(BaseModel):
    narrative: str
    vibes: list[str] = []
    clashes: list[str] = []
    title: str | None = None


class CompatibilityResult(BaseModel):
    user_a: UserPublic
    user_b: UserPublic
    overall_score: float = Field(ge=0, le=100)
    breakdown: dict[str, Any]
    overlap: OverlapBreakdown
    embedding: EmbeddingBreakdown
    audio_features: AudioFeatureBreakdown
    llm: LLMBreakdown | None = None
    generated_at: datetime
