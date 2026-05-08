import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { compare, profile } from "../api/client";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Pill } from "../components/Pill";
import { useAuthStatus } from "../hooks/useAuthStatus";
import type {
  AudioFeatureBreakdown,
  CompatibilityResult,
  EmbeddingBreakdown,
  LLMBreakdown,
  OverlapBreakdown,
  UserPublic,
} from "../api/types";
import styles from "./ComparePage.module.css";

const FEATURE_KEYS = [
  "danceability",
  "energy",
  "valence",
  "acousticness",
  "speechiness",
  "liveness",
] as const;

export function ComparePage() {
  const { userB: paramUserB } = useParams<{ userB?: string }>();
  const navigate = useNavigate();
  const { data: status } = useAuthStatus();

  const [selectedUser, setSelectedUser] = useState<string | null>(
    paramUserB ?? null,
  );
  const [includeLLM, setIncludeLLM] = useState(true);

  const usersQuery = useQuery({
    queryKey: ["profile", "list"],
    queryFn: () => profile.list(),
    enabled: status?.authenticated === true,
  });

  const compareMutation = useMutation({
    mutationFn: (params: { user_b: string; force?: boolean }) =>
      compare.run({
        user_b: params.user_b,
        include_llm: includeLLM,
        force: params.force ?? false,
      }),
  });

  // Auto-run if userB came from URL
  useEffect(() => {
    if (paramUserB && status?.authenticated && !compareMutation.data) {
      compareMutation.mutate({ user_b: paramUserB });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramUserB, status?.authenticated]);

  if (status && !status.authenticated) {
    return (
      <div className={`container ${styles.empty}`}>
        <h1 className="display-md">Sign in to compare.</h1>
        <p className="body-md">
          You need a Spotify-connected profile to run a compatibility report.
        </p>
        <a href="/api/auth/login">
          <Button variant="primary" size="lg">
            Connect with Spotify
          </Button>
        </a>
      </div>
    );
  }

  const result = compareMutation.data;

  return (
    <div className={`container ${styles.page}`}>
      {/* Header / Picker */}
      <div className={styles.head}>
        <div>
          <span className="caption-uppercase">Compatibility</span>
          <h1 className="display-lg">Compare taste profiles</h1>
          <p className="body-md">
            Pick someone who has connected their Spotify account. We'll blend
            overlap, embeddings and audio features into a single score.
          </p>
        </div>
      </div>

      <Card tone="cream" size="md" className={styles.pickerCard}>
        <div className={styles.pickerHead}>
          <span className="caption-uppercase">Choose a profile</span>
          <label className={styles.llmToggle}>
            <input
              type="checkbox"
              checked={includeLLM}
              onChange={(e) => setIncludeLLM(e.target.checked)}
            />
            <span className="caption">Include LLM narrative</span>
          </label>
        </div>
        <div className={styles.userGrid}>
          {usersQuery.isLoading && <p className="body-sm">Loading users…</p>}
          {usersQuery.data?.length === 0 && (
            <p className="body-sm">
              No other profiles yet. Share your link with a friend.
            </p>
          )}
          {usersQuery.data?.map((u) => (
            <UserChip
              key={u.user_id}
              user={u}
              selected={u.user_id === selectedUser}
              onSelect={() => {
                setSelectedUser(u.user_id);
                navigate(`/compare/${encodeURIComponent(u.user_id)}`, {
                  replace: true,
                });
                compareMutation.mutate({ user_b: u.user_id });
              }}
            />
          ))}
        </div>
        {selectedUser && (
          <div className={styles.pickerActions}>
            <Button
              variant="secondary"
              onClick={() =>
                compareMutation.mutate({ user_b: selectedUser, force: true })
              }
              disabled={compareMutation.isPending}
            >
              {compareMutation.isPending ? "Recomputing…" : "Force recompute"}
            </Button>
          </div>
        )}
      </Card>

      {compareMutation.isPending && (
        <Card tone="canvas" size="lg" className={styles.loadingCard}>
          <div className={styles.spinner} />
          <h2 className="title-lg">Crunching the numbers…</h2>
          <p className="body-sm">
            Fetching profiles, computing similarity, and asking Claude for a
            narrative.
          </p>
        </Card>
      )}

      {compareMutation.isError && (
        <Card tone="peach" size="md">
          <h3 className="title-lg">Something went wrong.</h3>
          <p className="body-sm">{(compareMutation.error as Error).message}</p>
        </Card>
      )}

      {result && <ResultView result={result} />}
    </div>
  );
}

function UserChip({
  user,
  selected,
  onSelect,
}: {
  user: UserPublic;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`${styles.userChip} ${selected ? styles.userChipSelected : ""}`}
    >
      {user.image_url ? (
        <img src={user.image_url} alt={user.display_name ?? user.user_id} />
      ) : (
        <div className={styles.userChipFallback}>
          {(user.display_name ?? user.user_id).slice(0, 1).toUpperCase()}
        </div>
      )}
      <span className="title-sm">{user.display_name ?? user.user_id}</span>
      {user.country && <span className="caption">{user.country}</span>}
    </button>
  );
}

function ResultView({ result }: { result: CompatibilityResult }) {
  const overall = Math.round(result.overall_score * 100);
  return (
    <div className={styles.result}>
      {/* Overall score orb */}
      <Card tone="lavender" size="lg" className={styles.scoreCard}>
        <div className={styles.scoreCardLeft}>
          <span className="caption-uppercase">Overall match</span>
          <h2 className="display-md" style={{ color: "inherit" }}>
            {result.user_a.display_name ?? result.user_a.user_id} ×{" "}
            {result.user_b.display_name ?? result.user_b.user_id}
          </h2>
          {result.llm?.title && (
            <p className="title-lg" style={{ marginTop: 8 }}>
              "{result.llm.title}"
            </p>
          )}
        </div>
        <div className={styles.scoreOrb}>
          <div className={styles.scoreOrbInner}>
            <span className={styles.scoreNumber}>{overall}</span>
            <span className="caption-uppercase">match</span>
          </div>
        </div>
      </Card>

      {/* Sub-scores row */}
      <div className={styles.subScoreRow}>
        <SubScoreCard
          tone="pink"
          label="Overlap"
          score={result.overlap.score}
          subtitle={`${result.overlap.shared_artists.length} shared artists`}
        />
        <SubScoreCard
          tone="teal"
          label="Embedding"
          score={result.embedding.score}
          subtitle={`${(result.embedding.similarity * 100).toFixed(0)}% similar`}
        />
        <SubScoreCard
          tone="ochre"
          label="Audio Features"
          score={result.audio_features.score}
          subtitle="cosine + tempo + loudness"
        />
      </div>

      {/* Detailed breakdowns */}
      <OverlapSection overlap={result.overlap} />
      <AudioFeaturesSection audio={result.audio_features} />
      <EmbeddingSection embedding={result.embedding} />
      {result.llm && <LLMSection llm={result.llm} />}

      <p className={styles.timestamp}>
        Generated {new Date(result.generated_at).toLocaleString()}
      </p>
    </div>
  );
}

function SubScoreCard({
  tone,
  label,
  score,
  subtitle,
}: {
  tone: "pink" | "teal" | "ochre";
  label: string;
  score: number;
  subtitle: string;
}) {
  return (
    <Card tone={tone} size="md" className={styles.subScoreCard}>
      <span className="caption-uppercase">{label}</span>
      <p className={styles.subScoreNumber}>{Math.round(score * 100)}</p>
      <p className="caption">{subtitle}</p>
    </Card>
  );
}

function OverlapSection({ overlap }: { overlap: OverlapBreakdown }) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h3 className="display-sm">Overlap</h3>
        <span className="caption">
          Artists {(overlap.artist_jaccard * 100).toFixed(0)}% · Tracks{" "}
          {(overlap.track_jaccard * 100).toFixed(0)}% · Genres{" "}
          {(overlap.genre_cosine * 100).toFixed(0)}%
        </span>
      </div>
      <div className={styles.overlapGrid}>
        <Card tone="canvas" size="md">
          <span className="caption-uppercase">Shared artists</span>
          {overlap.shared_artists.length === 0 ? (
            <p className="body-sm" style={{ marginTop: 8 }}>
              No overlap in top artists.
            </p>
          ) : (
            <div className={styles.pillRow}>
              {overlap.shared_artists.slice(0, 16).map((a) => (
                <Pill key={a.id} tone="pink">
                  {a.name}
                </Pill>
              ))}
            </div>
          )}
        </Card>
        <Card tone="canvas" size="md">
          <span className="caption-uppercase">Shared tracks</span>
          {overlap.shared_tracks.length === 0 ? (
            <p className="body-sm" style={{ marginTop: 8 }}>
              No overlap in top tracks.
            </p>
          ) : (
            <ul className={styles.trackList}>
              {overlap.shared_tracks.slice(0, 8).map((t) => (
                <li key={t.id}>
                  <p className="title-sm">{t.name}</p>
                  <p className="caption">{t.artist_names.join(", ")}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card tone="canvas" size="md">
          <span className="caption-uppercase">Shared genres</span>
          {overlap.shared_genres.length === 0 ? (
            <p className="body-sm" style={{ marginTop: 8 }}>
              No overlap in genres.
            </p>
          ) : (
            <div className={styles.pillRow}>
              {overlap.shared_genres.slice(0, 16).map((g) => (
                <Pill key={g} tone="lavender">
                  {g}
                </Pill>
              ))}
            </div>
          )}
        </Card>
      </div>
    </section>
  );
}

function AudioFeaturesSection({ audio }: { audio: AudioFeatureBreakdown }) {
  const rows = useMemo(
    () =>
      FEATURE_KEYS.map((key) => ({
        key,
        you: audio.your_vector[key],
        them: audio.their_vector[key],
        delta: audio.deltas[key] ?? Math.abs(audio.your_vector[key] - audio.their_vector[key]),
      })),
    [audio],
  );

  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h3 className="display-sm">Audio fingerprint diff</h3>
        <span className="caption">Closer bars = more aligned vibe</span>
      </div>
      <Card tone="cream" size="md">
        <div className={styles.featureCompareGrid}>
          {rows.map((r) => (
            <div key={r.key} className={styles.featureCompareRow}>
              <span className="caption" style={{ textTransform: "capitalize" }}>
                {r.key}
              </span>
              <div className={styles.dualBar}>
                <div
                  className={styles.dualBarYou}
                  style={{ width: `${Math.min(100, r.you * 100)}%` }}
                />
                <div
                  className={styles.dualBarThem}
                  style={{ width: `${Math.min(100, r.them * 100)}%` }}
                />
              </div>
              <span className="caption" style={{ minWidth: 48, textAlign: "right" }}>
                Δ {(r.delta * 100).toFixed(0)}
              </span>
            </div>
          ))}
        </div>
        <div className={styles.scalarRow}>
          <Pill tone="ink">
            You {audio.your_vector.tempo.toFixed(0)} BPM · Them{" "}
            {audio.their_vector.tempo.toFixed(0)} BPM
          </Pill>
          <Pill tone="ink">
            You {audio.your_vector.loudness.toFixed(1)} dB · Them{" "}
            {audio.their_vector.loudness.toFixed(1)} dB
          </Pill>
        </div>
        <div className={styles.legend}>
          <span className={styles.legendDotYou} /> You
          <span className={styles.legendDotThem} /> Them
        </div>
      </Card>
    </section>
  );
}

function EmbeddingSection({ embedding }: { embedding: EmbeddingBreakdown }) {
  const pct = Math.round(embedding.similarity * 100);
  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h3 className="display-sm">Embedding similarity</h3>
        <span className="caption">Sentence-transformers on taste cards</span>
      </div>
      <Card tone="teal" size="md" className={styles.embeddingCard}>
        <div className={styles.gauge}>
          <div className={styles.gaugeFill} style={{ width: `${pct}%` }} />
        </div>
        <p className="body-md" style={{ color: "inherit" }}>
          Your taste descriptions are <strong>{pct}%</strong> similar in latent
          space.
        </p>
      </Card>
    </section>
  );
}

function LLMSection({ llm }: { llm: LLMBreakdown }) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h3 className="display-sm">The narrative</h3>
        <span className="caption">By Claude</span>
      </div>
      <Card tone="peach" size="lg">
        <p className="body-md" style={{ color: "inherit" }}>
          {llm.narrative}
        </p>
        {llm.vibes.length > 0 && (
          <div className={styles.llmRow}>
            <span className="caption-uppercase">Vibes</span>
            <div className={styles.pillRow}>
              {llm.vibes.map((v) => (
                <Pill key={v} tone="mint">
                  {v}
                </Pill>
              ))}
            </div>
          </div>
        )}
        {llm.clashes.length > 0 && (
          <div className={styles.llmRow}>
            <span className="caption-uppercase">Clashes</span>
            <div className={styles.pillRow}>
              {llm.clashes.map((c) => (
                <Pill key={c} tone="pink">
                  {c}
                </Pill>
              ))}
            </div>
          </div>
        )}
      </Card>
    </section>
  );
}
