import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import styles from "./PostLoginPage.module.css";

export function PostLoginPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  useEffect(() => {
    qc.invalidateQueries({ queryKey: ["auth", "status"] });
    const t = setTimeout(() => navigate("/me", { replace: true }), 600);
    return () => clearTimeout(t);
  }, [navigate, qc]);

  return (
    <div className={`container ${styles.wrapper}`}>
      <div className={styles.spinner} />
      <h1 className="display-md">Connecting…</h1>
      <p className="body-md">Building your taste profile in a moment.</p>
    </div>
  );
}
