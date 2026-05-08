"""Build a TasteProfile for a user by orchestrating Spotify API calls + enrichment."""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone

from ..db import cursor, from_json, to_json
from ..schemas import (
    AudioFingerprint,
    TasteProfile,
    TopArtist,
    TopTrack,
    UserPublic,
)
from ..spotify.client import SpotifyClient
from ..spotify.enrich import enrich_artists, enrich_tracks

log = logging.getLogger(__name__)

TIME_RANGES = ("short_term", "medium_term", "long_term")


# ---------- Helpers ----------

def _artist_to_schema(a: dict) -> TopArtist:
    images = a.get("images") or []
    image_url = images[0]["url"] if images else None
    return TopArtist(
        id=a["id"],
        name=a.get("name") or "",
        genres=a.get("genres") or [],
        popularity=a.get("popularity"),
        image_url=image_url,
    )


def _cached_artist_to_schema(a: dict) -> TopArtist:
    return TopArtist(
        id=a["artist_id"],
        name=a.get("name") or "",
        genres=a.get("genres") or [],
        popularity=a.get("popularity"),
        image_url=a.get("image_url"),
    )


def _track_to_schema(t: dict) -> TopTrack:
    return TopTrack(
        uri=t.get("uri") or f"spotify:track:{t['id']}",
        id=t["id"],
        name=t.get("name") or "",
        artist_names=[a.get("name", "") for a in (t.get("artists") or [])],
        artist_ids=[a.get("id", "") for a in (t.get("artists") or [])],
        popularity=t.get("popularity"),
    )


def _avg(values: list[float]) -> float:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def _aggregate_audio(features: list[dict]) -> AudioFingerprint:
    if not features:
        return AudioFingerprint()
    return AudioFingerprint(
        danceability=_avg([f.get("danceability") for f in features]),
        energy=_avg([f.get("energy") for f in features]),
        valence=_avg([f.get("valence") for f in features]),
        acousticness=_avg([f.get("acousticness") for f in features]),
        instrumentalness=_avg([f.get("instrumentalness") for f in features]),
        liveness=_avg([f.get("liveness") for f in features]),
        speechiness=_avg([f.get("speechiness") for f in features]),
        tempo=_avg([f.get("tempo") for f in features]),
        loudness=_avg([f.get("loudness") for f in features]),
        sample_size=len([f for f in features if f]),
    )


def _genre_distribution(artists: list[dict]) -> dict[str, float]:
    counter: Counter[str] = Counter()
    for a in artists:
        for g in a.get("genres") or []:
            counter[g] += 1
    if not counter:
        return {}
    total = sum(counter.values())
    return {g: c / total for g, c in counter.most_common(50)}


# ---------- Main builder ----------

async def build_taste_profile(user_id: str) -> TasteProfile:
    """Fetch all relevant data from Spotify and assemble a TasteProfile."""
    log.info("Building taste profile for %s", user_id)
    async with SpotifyClient(user_id) as sp:
        me = await sp.me()

        # Fetch top artists & tracks for all 3 time ranges in parallel
        artist_tasks = [sp.top_artists(time_range=tr, limit=50) for tr in TIME_RANGES]
        track_tasks = [sp.top_tracks(time_range=tr, limit=50) for tr in TIME_RANGES]
        artist_results, track_results = await asyncio.gather(
            asyncio.gather(*artist_tasks),
            asyncio.gather(*track_tasks),
        )
        top_artists_by_range = dict(zip(TIME_RANGES, artist_results))
        top_tracks_by_range = dict(zip(TIME_RANGES, track_results))

        # Pool tracks for audio-feature enrichment (de-duped)
        all_tracks: dict[str, dict] = {}
        for tracks in top_tracks_by_range.values():
            for t in tracks:
                if t.get("id"):
                    all_tracks[t["id"]] = t
        features_by_id = await enrich_tracks(sp, list(all_tracks.values()))

        # Collect artist ids needing genre enrichment (some come without genres
        # from /me/top/artists, but most have them; we still ensure cache)
        artist_ids_needing_info: set[str] = set()
        for tracks in top_tracks_by_range.values():
            for t in tracks:
                for a in t.get("artists") or []:
                    if a.get("id"):
                        artist_ids_needing_info.add(a["id"])
        cached_artists = await enrich_artists(sp, list(artist_ids_needing_info))

    # Build profile
    user = UserPublic(
        user_id=me["id"],
        display_name=me.get("display_name"),
        image_url=(me.get("images") or [{}])[0].get("url") if me.get("images") else None,
        country=me.get("country"),
    )

    # Schema conversions
    top_artists_short = [_artist_to_schema(a) for a in top_artists_by_range["short_term"]]
    top_artists_medium = [_artist_to_schema(a) for a in top_artists_by_range["medium_term"]]
    top_artists_long = [_artist_to_schema(a) for a in top_artists_by_range["long_term"]]

    top_tracks_short = [_track_to_schema(t) for t in top_tracks_by_range["short_term"]]
    top_tracks_medium = [_track_to_schema(t) for t in top_tracks_by_range["medium_term"]]
    top_tracks_long = [_track_to_schema(t) for t in top_tracks_by_range["long_term"]]

    # Genre distribution: weight by union of top-artists across all ranges + cached track artists
    genre_source: list[dict] = []
    for tr in TIME_RANGES:
        genre_source.extend(top_artists_by_range[tr])
    # Add cached artist genres (covers track-only artists)
    for aid, info in cached_artists.items():
        genre_source.append({"genres": info.get("genres") or []})
    genres = _genre_distribution(genre_source)

    # Audio fingerprint from medium_term top tracks (most stable)
    medium_features = [
        features_by_id[t["id"]]
        for t in top_tracks_by_range["medium_term"]
        if t.get("id") in features_by_id
    ]
    fingerprint = _aggregate_audio(medium_features)

    profile = TasteProfile(
        user=user,
        top_artists_short=top_artists_short,
        top_artists_medium=top_artists_medium,
        top_artists_long=top_artists_long,
        top_tracks_short=top_tracks_short,
        top_tracks_medium=top_tracks_medium,
        top_tracks_long=top_tracks_long,
        genres=genres,
        audio_fingerprint=fingerprint,
        built_at=datetime.now(timezone.utc),
    )
    save_profile(profile)
    return profile


# ---------- Persistence ----------

def save_profile(profile: TasteProfile) -> None:
    now = datetime.now(timezone.utc)
    with cursor() as c:
        c.execute(
            """
            INSERT INTO taste_profiles (user_id, profile_json, built_at)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                profile_json = excluded.profile_json,
                built_at     = excluded.built_at
            """,
            [profile.user.user_id, profile.model_dump_json(), now],
        )


def load_profile(user_id: str) -> TasteProfile | None:
    with cursor() as c:
        row = c.execute(
            "SELECT profile_json FROM taste_profiles WHERE user_id = ?", [user_id]
        ).fetchone()
    if not row:
        return None
    return TasteProfile.model_validate_json(row[0])


async def get_or_build_profile(user_id: str, force: bool = False) -> TasteProfile:
    if not force:
        cached = load_profile(user_id)
        if cached:
            return cached
    return await build_taste_profile(user_id)
