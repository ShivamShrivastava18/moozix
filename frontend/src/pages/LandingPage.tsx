import { Link } from "react-router-dom";

import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Pill } from "../components/Pill";
import styles from "./LandingPage.module.css";

export function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className={styles.hero}>
        <div className={`container ${styles.heroInner}`}>
          <div className={styles.heroLeft}>
            <Pill tone="default">Cross-User Spotify Compatibility Engine</Pill>
            <h1 className="display-xl">
              How musically
              <br />
              compatible
              <br />
              <em className={styles.italic}>are you, really?</em>
            </h1>
            <p className={`body-md ${styles.lede}`}>
              moozix builds a deep taste profile for each of you, runs four
              different similarity engines in parallel, then writes a witty
              compatibility report grounded in actual shared artists, tracks,
              and audio moods.
            </p>
            <div className={styles.ctas}>
              <a href="/api/auth/login">
                <Button variant="primary" size="lg">
                  Connect with Spotify
                </Button>
              </a>
              <Link to="/compare">
                <Button variant="secondary" size="lg">
                  See a sample report
                </Button>
              </Link>
            </div>
            <p className={`caption ${styles.disclaimer}`}>
              Read-only Spotify access · No data shared without your action ·
              Built by{" "}
              <a
                href="https://github.com/ShivamShrivastava18"
                target="_blank"
                rel="noreferrer"
              >
                @ShivamShrivastava18
              </a>
            </p>
          </div>

          <div className={styles.heroRight} aria-hidden="true">
            <div className={styles.scoreOrb}>
              <div className={styles.scoreOrbInner}>
                <span className={styles.scoreNumber}>87</span>
                <span className="caption-uppercase">Compatibility</span>
              </div>
            </div>
            <div className={styles.floatPill1}>
              <Pill tone="pink">indie pop overlap</Pill>
            </div>
            <div className={styles.floatPill2}>
              <Pill tone="ochre">+ shared 12 artists</Pill>
            </div>
            <div className={styles.floatPill3}>
              <Pill tone="mint">audio mood match</Pill>
            </div>
          </div>
        </div>
      </section>

      {/* Four-method explainer */}
      <section className={styles.methods}>
        <div className="container">
          <div className={styles.methodsHead}>
            <span className="caption-uppercase">How it works</span>
            <h2 className="display-md">
              Four signals. One score.
              <br />
              Plus a story you can argue with.
            </h2>
          </div>

          <div className={styles.methodGrid}>
            <Card tone="pink" size="lg" className={styles.methodCard}>
              <span className="caption-uppercase">01 · Overlap</span>
              <h3 className="display-sm" style={{ color: "inherit" }}>
                Shared artists, tracks, genres
              </h3>
              <p className={`body-md ${styles.methodBody}`}>
                Jaccard on artists and tracks, cosine on weighted genres. The
                most concrete signal — pulls out the names you both already
                love.
              </p>
            </Card>

            <Card tone="lavender" size="lg" className={styles.methodCard}>
              <span className="caption-uppercase">02 · Embedding</span>
              <h3 className="display-sm" style={{ color: "inherit" }}>
                Semantic taste cards
              </h3>
              <p className={`body-md ${styles.methodBody}`}>
                Each profile becomes a textual taste card; sentence-transformers
                embed both and compare. Captures vibes that don't share a
                literal track.
              </p>
            </Card>

            <Card tone="peach" size="lg" className={styles.methodCard}>
              <span className="caption-uppercase">03 · Audio fingerprint</span>
              <h3 className="display-sm" style={{ color: "inherit" }}>
                Energy, valence, danceability
              </h3>
              <p className={`body-md ${styles.methodBody}`}>
                Aggregates Spotify's audio features across your top tracks into
                a 9-D fingerprint, then compares with cosine plus per-feature
                deltas.
              </p>
            </Card>

            <Card tone="teal" size="lg" className={styles.methodCard}>
              <span
                className="caption-uppercase"
                style={{ color: "var(--color-on-dark-soft)" }}
              >
                04 · Narrative
              </span>
              <h3 className="display-sm" style={{ color: "inherit" }}>
                A Claude-written report
              </h3>
              <p
                className={`body-md ${styles.methodBody}`}
                style={{ color: "var(--color-on-dark-soft)" }}
              >
                A short, opinionated essay calling out the vibes you share and
                the genres where you'd fight in the car. Specific, never
                generic.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Stack strip */}
      <section className={styles.stack}>
        <div className="container">
          <div className={styles.stackInner}>
            <Card tone="cream" size="lg" className={styles.stackCard}>
              <span className="caption-uppercase">Backend</span>
              <h3 className="title-lg">FastAPI · DuckDB · httpx</h3>
              <p className="body-sm">
                Async Spotify Web API client with retries and rate-limit
                handling. Aggressive caching of audio features and artist
                genres.
              </p>
            </Card>
            <Card tone="cream" size="lg" className={styles.stackCard}>
              <span className="caption-uppercase">AI</span>
              <h3 className="title-lg">
                sentence-transformers · Anthropic Claude
              </h3>
              <p className="body-sm">
                MiniLM embeddings for semantic similarity. Claude generates the
                narrative grounded in real, quantitative signals.
              </p>
            </Card>
            <Card tone="cream" size="lg" className={styles.stackCard}>
              <span className="caption-uppercase">Frontend</span>
              <h3 className="title-lg">React · Vite · Clay design</h3>
              <p className="body-sm">
                Cream-canvas visual system with saturated card accents. Styled
                with the getdesign clay design language.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA band */}
      <section className={styles.ctaBand}>
        <div className="container">
          <Card tone="soft" size="lg" className={styles.ctaCard}>
            <div>
              <h2 className="display-md">Ready to find out?</h2>
              <p className="body-md">
                Connect Spotify, build your taste profile in seconds, and send a
                share link to your friend.
              </p>
            </div>
            <a href="/api/auth/login">
              <Button variant="primary" size="lg">
                Connect with Spotify
              </Button>
            </a>
          </Card>
        </div>
      </section>

      <footer className={styles.footer}>
        <div className="container">
          <div className={styles.footerInner}>
            <span className="caption">moozix · 2026</span>
            <span className="caption">
              Not affiliated with Spotify. Built for fun.
            </span>
          </div>
        </div>
      </footer>
    </>
  );
}
