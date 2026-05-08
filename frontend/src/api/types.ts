// Mirrors backend Pydantic schemas in app/schemas.py

export interface UserPublic {
  user_id: string;
  display_name?: string | null;
  image_url?: string | null;
  country?: string | null;
}

export interface TopArtist {
  id: string;
  name: string;
  genres: string[];
  popularity?: number | null;
  image_url?: string | null;
}

export interface TopTrack {
  uri: string;
  id: string;
  name: string;
  artist_names: string[];
  artist_ids: string[];
  popularity?: number | null;
}

export interface AudioFingerprint {
  danceability: number;
  energy: number;
  valence: number;
  acousticness: number;
  instrumentalness: number;
  liveness: number;
  speechiness: number;
  tempo: number;
  loudness: number;
  sample_size: number;
}

export interface TasteProfile {
  user: UserPublic;
  top_artists_short: TopArtist[];
  top_artists_medium: TopArtist[];
  top_artists_long: TopArtist[];
  top_tracks_short: TopTrack[];
  top_tracks_medium: TopTrack[];
  top_tracks_long: TopTrack[];
  genres: Record<string, number>;
  audio_fingerprint: AudioFingerprint;
  built_at?: string | null;
}

export interface OverlapBreakdown {
  score: number;
  artist_jaccard: number;
  track_jaccard: number;
  genre_cosine: number;
  shared_artists: TopArtist[];
  shared_tracks: TopTrack[];
  shared_genres: string[];
}

export interface EmbeddingBreakdown {
  score: number;
  similarity: number;
}

export interface AudioFeatureBreakdown {
  score: number;
  your_vector: AudioFingerprint;
  their_vector: AudioFingerprint;
  deltas: Record<string, number>;
}

export interface LLMBreakdown {
  narrative: string;
  vibes: string[];
  clashes: string[];
  title?: string | null;
}

export interface CompatibilityResult {
  user_a: UserPublic;
  user_b: UserPublic;
  overall_score: number;
  breakdown: Record<string, unknown>;
  overlap: OverlapBreakdown;
  embedding: EmbeddingBreakdown;
  audio_features: AudioFeatureBreakdown;
  llm?: LLMBreakdown | null;
  generated_at: string;
}

export interface AuthStatus {
  authenticated: boolean;
  user?: { user_id: string; display_name?: string | null; image_url?: string | null };
}
