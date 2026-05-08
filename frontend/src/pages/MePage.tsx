import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { profile } from "../api/client";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Pill } from "../components/Pill";
import { useAuthStatus } from "../hooks/useAuthStatus";
import styles from "./MePage.module.css";

export function MePage() {
  const { data: status } = useAuthStatus();
  const qc = useQueryClient();

  const meQuery = useQuery({
    queryKey: ["profile", "me"],
    queryFn: () => profile.me(false),
    enabled: status?.authenticated === true,
  });

  const refreshMutation = useMutation({
    mutationFn: () => profile.refresh(),
    onSuccess: (data) => {
      qc.setQueryData(["profile", "me"], data);
    },
  });

  if (status && !status.authenticated) {
    return (
      <div className={`container ${styles.empty}`}>
        <h1 className="display-md">You're not connected.</h1>
        <p className="body-md">Connect your Spotify account to build a taste profile.</p>
        <a href="/api/auth/login">
          <Button variant="primary" size="lg">
            Connect with Spotify
          </Button>
        </a>
      </div>
    );
  }

  if (!meQuery.data) {
    return (
      <div className={`container ${styles.loading}`}>
        <div className={styles.spinner} />
        <h2 className="title-lg">Building your taste profile…</h2>
        <p className="body-sm">Fetching top artists, tracks, and audio features. ~10 seconds.</p>
      </div>
    );
  }

  const p = meQuery.data;
  const fp = p.audio_fingerprint;
  const topGenres = Object.entries(p.genres)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);

  return (
    <div className={`container ${styles.page}`}>
      {/* Header */}
      <div className={styles.head}>
        <div className={styles.headLeft}>
          {p.user.image_url ? (
            <img src={p.user.image_url} alt={p.user.display_name ?? "you"} />
          ) : (
            <div className={styles.avatarFallback}>
              {(p.user.display_name ?? "?").slice(0, 1).toUpperCase()}
            </div>
          )}
          <div>
            <span className="caption-uppercase">Your taste profile</span>
            <h1 className="display-lg">{p.user.display_name ?? p.user.user_id}</h1>
            <p className="body-sm">
              Built {p.built_at ? new Date(p.built_at).toLocaleString() : "just now"} · Sample
              size {fp.sample_size} tracks
            </p>
          </div>
        </div>
        <div className={styles.headRight}>
          <Button
            variant="secondary"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
          >
            {refreshMutation.isPending ? "Refreshing…" : "Refresh"}
          </Button>
          <Link to="/compare">
            <Button variant="primary">Compare with someone</Button>
          </Link>
        </div>
      </div>

      {/* Audio fingerprint card */}
      <Card tone="lavender" size="lg" className={styles.fingerprintCard}>
        <div className={styles.fingerprintHead}>
          <span className="caption-uppercase">Audio fingerprint</span>
          <h2 className="display-sm" style={{ color: "inherit" }}>
            How your music feels
          </h2>
        </div>
        <div className={styles.featureGrid}>
          {(
            [
              ["Danceability", fp.danceability],
              ["Energy", fp.energy],
              ["Valence", fp.valence],
              ["Acousticness", fp.acousticness],
              ["Speechiness", fp.speechiness],
              ["Liveness", fp.liveness],
            ] as const
          ).map(([label, val]) => (
            <FeatureBar key={label} label={label} value={val} />
          ))}
        </div>
        <div className={styles.scalarFeatures}>
          <Pill tone="ink">{fp.tempo.toFixed(0)} BPM</Pill>
          <Pill tone="ink">{fp.loudness.toFixed(1)} dB</Pill>
        </div>
      </Card>

      {/* Top artists */}
      <section className={styles.section}>
        <div className={styles.sectionHead}>
          <h2 className="display-sm">Your top artists</h2>
          <span className="caption-uppercase">Last 6 months</span>
        </div>
        <div className={styles.artistGrid}>
          {p.top_artists_medium.slice(0, 12).map((a, i) => (
            <ArtistCard key={a.id} artist={a} rank={i + 1} />
          ))}
        </div>
      </section>

      {/* Top tracks + genres side by side */}
      <section className={styles.twoCol}>
        <div>
          <div className={styles.sectionHead}>
            <h2 className="display-sm">Top tracks</h2>
          </div>
          <Card tone="canvas" size="md" padded={false}>
            <ol className={styles.trackList}>
              {p.top_tracks_medium.slice(0, 10).map((t, i) => (
                <li key={t.id}>
                  <span className={styles.rank}>{(i + 1).toString().padStart(2, "0")}</span>
                  <div>
                    <p className="title-sm">{t.name}</p>
                    <p className="caption">{t.artist_names.join(", ")}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <div>
          <div className={styles.sectionHead}>
            <h2 className="display-sm">Top genres</h2>
          </div>
          <Card tone="cream" size="md" className={styles.genres}>
            {topGenres.length === 0 ? (
              <p className="body-sm">No genre data yet. Try refreshing.</p>
            ) : (
              <div className={styles.genrePillRow}>
                {topGenres.map(([g, w], i) => (
                  <Pill
                    key={g}
                    tone={
                      (
                        ["pink", "lavender", "ochre", "mint", "teal"] as const
                      )[i % 5]
                    }
                  >
                    {g} · {Math.round(w * 100)}
                  </Pill>
                ))}
              </div>
            )}
          </Card>
        </div>
      </section>
    </div>
  );
}

function FeatureBar({ label, value }: { label: string; value: number }) {
  return (
    <div className={styles.featureRow}>
      <span className="caption">{label}</span>
      <div className={styles.bar}>
        <div className={styles.barFill} style={{ width: `${Math.min(100, value * 100)}%` }} />
      </div>
      <span className="caption" style={{ minWidth: 36, textAlign: "right" }}>
        {Math.round(value * 100)}
      </span>
    </div>
  );
}

function ArtistCard({
  artist,
  rank,
}: {
  artist: { name: string; image_url?: string | null; genres: string[] };
  rank: number;
}) {
  return (
    <Card tone="canvas" size="sm" className={styles.artistCard}>
      <div className={styles.artistImageWrap}>
        {artist.image_url ? (
          <img src={artist.image_url} alt={artist.name} />
        ) : (
          <div className={styles.artistFallback}>{artist.name.slice(0, 1)}</div>
        )}
        <span className={styles.artistRank}>#{rank}</span>
      </div>
      <p className="title-sm" style={{ marginTop: 8 }}>
        {artist.name}
      </p>
      <p className="caption">{artist.genres.slice(0, 2).join(", ")}</p>
    </Card>
  );
}
