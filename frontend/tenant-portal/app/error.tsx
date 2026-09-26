"use client";

import Link from "next/link";
import { useEffect } from "react";
import styles from "./error-state.module.css";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Tenant portal route failed", error);
  }, [error]);

  return <main className={styles.viewport}>
    <section className={styles.card} role="alert" aria-labelledby="error-title">
      <span className={styles.code}>ERROR</span>
      <h1 id="error-title">We couldn&apos;t load this page</h1>
      <p>Your data is safe. Try the request again, or return to the dashboard if the problem continues.</p>
      <div className={styles.actions}>
        <button className={styles.primary} type="button" onClick={reset}>Try again</button>
        <Link className={styles.secondary} href="/dashboard">Back to dashboard</Link>
      </div>
    </section>
  </main>;
}
