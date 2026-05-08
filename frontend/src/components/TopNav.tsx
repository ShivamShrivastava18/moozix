import { Link } from "react-router-dom";
import { Button } from "./Button";
import styles from "./TopNav.module.css";

interface TopNavProps {
  authenticated?: boolean;
  user?: { display_name?: string | null; image_url?: string | null } | null;
}

export function TopNav({ authenticated, user }: TopNavProps) {
  return (
    <header className={styles.nav}>
      <div className={styles.inner}>
        <Link to="/" className={styles.brand} aria-label="moozix home">
          <span className={styles.logoDot} />
          <span className={styles.wordmark}>moozix</span>
        </Link>

        <nav className={styles.menu}>
          <Link to="/compare" className={styles.link}>
            Compare
          </Link>
          <a
            href="https://github.com/ShivamShrivastava18/moozix"
            target="_blank"
            rel="noreferrer"
            className={styles.link}
          >
            GitHub
          </a>
        </nav>

        <div className={styles.right}>
          {authenticated ? (
            <Link to="/me" className={styles.profile}>
              {user?.image_url ? (
                <img
                  src={user.image_url}
                  alt={user.display_name ?? "you"}
                  className={styles.avatar}
                />
              ) : (
                <span className={styles.avatarFallback}>
                  {(user?.display_name ?? "?").slice(0, 1).toUpperCase()}
                </span>
              )}
              <span className={styles.profileName}>
                {user?.display_name ?? "You"}
              </span>
            </Link>
          ) : (
            <a href="/api/auth/login">
              <Button variant="primary" size="md">
                Connect Spotify
              </Button>
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
